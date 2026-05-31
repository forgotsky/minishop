# SHOP-001 Implementation Summary

**Author:** Developer
**Date:** 2026-05-31
**Status:** ✅ Complete

---

## 涉及文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `backend/app/auth.py` | 新建 | JWT 签发、解析、认证中间件 |
| `backend/app/models.py` | 新建 User 表 | openid unique, nickname, avatar |
| `backend/app/main.py` | 新增 `/api/auth/login` | 241-266 行，微信登录接口 |
| `backend/app/main.py` | 多处 | 受保护接口添加 `require_user` 依赖 |
| `wechat-miniprogram/app.js` | 新建 | autoLogin, devLogin, globalData |
| `wechat-miniprogram/utils/api.js` | 新建 | request 封装 + token 管理 + handle401 |

---

## 关键代码片段

### 后端登录（main.py:241-266）
```python
@app.post("/api/auth/login", response_model=LoginOut)
def wx_login(payload: WxLoginIn, ...):
    mock_openid = f"wx_{payload.code}" if payload.code else f"wx_dev_{int(time.time())}"
    user = db.query(User).filter(User.openid == mock_openid).first()
    if not user:
        user = User(openid=mock_openid, nickname=payload.nickname, avatar=payload.avatar)
        db.add(user)
        db.commit()
    token = create_access_token(user.id)
    return LoginOut(token=token, user_id=user.id, nickname=user.nickname)
```

### 前端自动登录（app.js:8-22）
```javascript
autoLogin() {
  wx.login({
    success: (res) => {
      if (res.code) {
        api.login(res.code, '', '').then(data => {
          wx.setStorageSync('token', data.token)
          this.globalData.loggedIn = true
        }).catch(() => this.devLogin())
      } else { this.devLogin() }
    },
    fail: () => this.devLogin()
  })
}
```

### 401 自动重登（api.js:3-8）
```javascript
const handle401 = () => {
  wx.removeStorageSync('token')
  getApp().globalData.loggedIn = false
  getApp().devLogin()
}
```

---

## 已实现的保护接口

| 接口 | 认证要求 |
|------|---------|
| GET/POST/PUT/DELETE `/api/cart/*` | require_user |
| POST `/api/orders` | require_user |
| GET `/api/orders` | require_user |
| POST `/api/orders/{id}/pay` | require_user |
| POST `/api/coupons/{id}/claim` | require_user |
| GET `/api/user/coupons` | require_user |
| CRUD `/api/addresses` | require_user |
| GET `/api/products` | 无需登录 |
| POST `/api/auth/login` | 无需登录 |
| GET `/api/health` | 无需登录 |

---

## 未完成项（Future Work）

- [ ] 接入真实微信 API（当前为 mock openid）
- [ ] JWT_SECRET_KEY 外部化到 K8s Secret
- [ ] 登录日志记录（登录时间、IP）
- [ ] 用户协议/隐私政策弹窗

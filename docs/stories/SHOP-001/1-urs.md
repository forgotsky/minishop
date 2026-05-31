# SHOP-001 User Requirement Specification

## Feature: 微信小程序用户登录认证授权

**Author:** Business Analyst
**Date:** 2026-05-31
**Status:** ✅ Implemented

---

## 用户故事

### US-001: 新用户首次登录

**As a** 微信小程序新用户
**I want to** 打开小程序后自动完成登录
**So that** 我可以浏览商品并下单，无需手动注册

### US-002: 老用户回访

**As a** 已登录过的用户
**I want to** 再次打开小程序时自动识别我的身份
**So that** 我的购物车、订单、优惠券都能保留

### US-003: API 接口认证保护

**As a** 系统管理员
**I want to** 敏感接口（下单、领券、查看订单）需要登录才能访问
**So that** 未登录用户无法操作需要身份的功能

---

## 验收标准

### AC-001: 自动登录流程

| Given | When | Then |
|-------|------|------|
| 用户首次打开小程序 | 点击任意页面 | 自动调用 wx.login() → 后端创建用户 → 返回 JWT token → 本地存储 |

### AC-002: Token 持久化

| Given | When | Then |
|-------|------|------|
| 用户已登录，关闭小程序 | 24 小时后重新打开 | JWT token 仍有效（720 小时过期），自动恢复登录态 |

### AC-003: 未登录拦截

| Given | When | Then |
|-------|------|------|
| 用户 token 过期 | 点击"领券"按钮 | 返回 401 → 前端自动清除旧 token → 重新登录 → 可继续操作 |

### AC-004: 开发环境兼容

| Given | When | Then |
|-------|------|------|
| 微信开发者工具测试环境 | wx.login() 返回测试 code 或失败 | 自动降级到 devLogin()，用 dev_ 前缀生成测试用户 |

---

## Scope

**In:**
- 微信小程序端自动登录（wx.login）
- 后端 JWT 认证（python-jose + HS256）
- Token 存储（wx.setStorageSync）和自动携带（Authorization: Bearer）
- 开发环境降级登录（devLogin）
- 401 自动重登机制
- 认证中间件：require_user（必须登录）、get_current_user（可选登录）

**Out:**
- 微信手机号授权（需要企业认证小程序）
- 微信支付（后续独立 Story）
- 第三方登录（Apple ID、手机号）
- 多设备同时登录管理

---

## Dependencies

| 依赖 | 状态 | 说明 |
|------|------|------|
| 微信小程序 AppID | ✅ | wx8504a60e24a072b4 |
| HTTPS 证书 | ✅ | Let's Encrypt via cert-manager |
| 后端 `/api/auth/login` 接口 | ✅ | 已实现 |
| JWT 密钥 | ⚠️ | 当前用 `dev-secret-change-in-production`，生产环境应改为强随机密钥 |

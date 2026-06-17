# SHOP-002 User Requirement Specification

## Feature: 补齐测试用例 + 测试自动化流水线

**Author:** Business Analyst
**Date:** 2026-06-01
**Status:** 🔄 In Progress

---

## 用户故事

### US-001: 后端 API 单元测试

**As a** 后端开发人员
**I want to** 每个 API 模块都有 pytest 单元测试
**So that** 改代码时能立刻发现回归问题

### US-002: API 集成模拟测试

**As a** 测试工程师
**I want to** 自动运行完整用户流程的 API 模拟脚本
**So that** 不用手动点页面就能验证全链路

### US-003: 测试门禁

**As a** Scrum Master
**I want to** 代码在审查前必须通过全部测试
**So that** Reviewer 不需要浪费时间检查低级 bug

### US-004: Review 后自动补测

**As a** 开发者
**I want to** Reviewer 修完 bug 后自动重新跑测试
**So that** 修 bug 不会引入新问题

---

## 验收标准

| ID | Given | When | Then |
|----|-------|------|------|
| AC-001 | 执行 pytest | 所有测试文件 | 0 failures |
| AC-002 | 运行模拟脚本 | 模拟登录→浏览→加购→下单→支付 | 每步输出 PASS |
| AC-003 | Dev 提交代码 | 触发测试 | 不通过则阻塞 Review |
| AC-004 | Reviewer 修完 | 重新跑测试 | 通过才能 commit |

---

## Scope

**In:**
- pytest 测试：auth, products, cart, orders, coupons, addresses, profile
- API 模拟脚本（httpx）：完整用户购物流程
- 测试报告生成
- 测试-修复-重测循环

**Out:**
- 前端 WeChat 小程序 UI 自动化（微信不开放）
- 性能/压力测试
- E2E 真机测试

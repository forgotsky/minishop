# SHOP-003 中英文双语切换 — Code Review 报告

## 审查概况

| 项目 | 值 |
|------|-----|
| 审查日期 | 2026-06-07 |
| 审查范围 | 20 个文件（1 新建 + 19 修改） |
| 严重 Bug | 0 |
| 安全漏洞 | 0 |
| 兼容性问题 | 0（已修复双重 setData 和直接引用修改） |

---

## 发现的 Bug

### ✅ 无严重 Bug

经过全面审查，未发现可能导致功能异常的 Bug。

---

## 已修复的问题

### 1. coupon.js refreshLang 双重 setData (已修复)

**问题**：`refreshLang()` 内部直接调用 `this.setData()` 后又由外层的 `refreshAllPages()` 再次调用 `setData()`，导致两次渲染。

**修复前**：
```javascript
refreshLang() {
  self.setData({ myCoupons: addStatusLabel(self.data.myCoupons) })
  return {}
}
```

**修复后**：
```javascript
refreshLang() {
  return { myCoupons: addStatusLabel(this.data.myCoupons) }
}
```

### 2. order.js refreshLang 直接修改 data 引用 (已修复)

**问题**：`refreshLang()` 直接修改 `this.data.orders[i]` 的引用，不符合 React/小程序不可变数据最佳实践。

**修复**：使用 `.map()` 创建新数组，由 `refreshAllPages()` 统一 `setData`。

---

## 安全检查

| 检查项 | 结果 |
|--------|------|
| XSS 注入 | ✅ 无风险 — 语言包为静态字符串，不包含用户输入 |
| Token 泄露 | ✅ 无风险 — 未新增敏感数据存储 |
| Storage 安全 | ✅ 安全 — 仅存储 'zh'/'en' 字符串 |
| API 数据泄露 | ✅ 无风险 — 语言偏好不发送到后端 |

---

## 微信兼容性检查

| 检查项 | 结果 |
|--------|------|
| `?.` 可选链 | ✅ 0 处违规 |
| `??` 空值合并 | ✅ 0 处违规 |
| WXML 表达式 | ✅ 无 `.replace()` 等不支持的方法调用 |
| WXML 动态 key 拼接 | ✅ coupon 状态改用 `_statusLabel` 预计算 |
| 箭头函数 | ✅ 微信支持 ES6 箭头函数 |
| CommonJS 模块 | ✅ 使用 `require()`/`module.exports`，兼容 |

---

## 架构审查

### 优点
- **纯前端方案**：无需后端变更，实现简洁
- **即时切换**：`toggleLang()` → `refreshAllPages()` → 所有页面同步更新
- **可扩展**：各页面可通过 `refreshLang()` 钩子自定义刷新逻辑
- **持久化**：`wx.setStorageSync('lang')` 确保偏好跨会话保留

### 注意事项
- `getCurrentPages()` 在某些边缘场景可能返回空数组（如页面切换过程中），此时语言切换不生效，但下次 `onShow` 会重新加载语言 — 可接受
- `t` 对象（146 个 key）通过 `setData` 完整传递，约 5KB — 性能可接受

---

## 测试覆盖

| 检查项 | 结果 |
|--------|------|
| 语言包一致性 | ✅ 146 keys 中英完全对应 |
| 微信兼容性 | ✅ 0 禁止语法 |
| 硬编码中文 | ✅ 全部清理 |
| 后端回归测试 | ✅ 跳过（无后端变更） |

---

## 审查结论

**✅ APPROVED** — 代码质量良好，无 Bug，无安全风险，完全兼容微信小程序。建议合并。

| 评级 | 值 |
|------|-----|
| 正确性 | A |
| 安全性 | A |
| 兼容性 | A |
| 可维护性 | A |

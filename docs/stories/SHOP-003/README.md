# SHOP-003: 中英文双语切换

## 概述

为 MiniShop 微信小程序添加中英文双语切换功能。用户点击首页 "中/EN" 按钮即可切换 UI 语言，切换即时生效，偏好自动持久化。

## 技术方案

- **纯前端实现**，无需后端变更
- 语言包定义在 `utils/i18n.js`（146 个 key）
- 语言偏好存储在 `wx.setStorageSync('lang')`
- 切换时通过 `getCurrentPages()` 遍历所有页面同步更新

## 文件变更

| 文件 | 变更 | 说明 |
|------|------|------|
| `utils/i18n.js` | **新建** | 语言包 + 翻译函数 |
| `app.js` | 修改 | 全局语言状态初始化 + `setAppLang()` |
| `pages/index/index.wxml` | 修改 | 所有文本 → `{{t.xxx}}`，新增语言切换按钮 |
| `pages/index/index.js` | 修改 | i18n 集成 + `onSwitchLang()` |
| `pages/product/product.*` | 修改 | 翻译按钮文本 + Toast |
| `pages/cart/cart.*` | 修改 | 翻译标签 + Toast |
| `pages/checkout/checkout.*` | 修改 | 全部表单标签翻译 |
| `pages/order/order.*` | 修改 | STATUS_LABELS 动态化 + itemCount 翻译 |
| `pages/order-detail/order-detail.*` | 修改 | 全部中文 toast/modal 翻译 |
| `pages/coupon/coupon.*` | 修改 | 状态标签 + Claim 消息翻译 |
| `pages/address/address.*` | 修改 | 标题 + 对话框翻译 |
| `pages/address-edit/address-edit.*` | 修改 | 表单字段标签 + placeholder 翻译 |

## API 文档

无新增 API。语言切换为纯客户端功能。

## 如何使用

### 前端

```javascript
// JS 中使用翻译
const { t } = require('../../utils/i18n')
wx.showToast({ title: t('toast.addedToCart'), icon: 'success' })

// WXML 中使用翻译（需在 Page data 中设置 t）
// Page: this.setData({ t: getAllTexts() })
// WXML: <text>{{t.cart.empty}}</text>

// 切换语言
const { toggleLang } = require('../../utils/i18n')
toggleLang() // zh ↔ en
```

### 语言切换流程
1. 用户在首页点击 "中/EN" 按钮
2. `toggleLang()` 切换 Storage 中的 `lang` 值
3. `refreshAllPages()` 遍历页面栈更新 `t` 数据
4. 各页面 WXML 自动刷新为对应语言

## 测试

### 语言包验证
```bash
node -e "验证 146 个 key 中英对应"  # ✅ PASS
```

### 微信兼容性
- `?.` 可选链: 0 处违规 ✅
- `??` 空值合并: 0 处违规 ✅

### 手动测试清单
- [ ] 首次打开 → 中文界面
- [ ] 点击 EN → 全英文
- [ ] 关闭重开 → 保持英文
- [ ] 订单状态标签切换正确
- [ ] Toast 消息语言正确
- [ ] 优惠券状态标签切换正确

## 详细文档

| 文档 | 路径 |
|------|------|
| URS | [1-urs.md](./1-urs.md) |
| Story 拆分 | [2-story.md](./2-story.md) |
| 架构设计 | [3-architecture.md](./3-architecture.md) |
| 测试报告 | [5-tests.md](./5-tests.md) |
| Code Review | [6-review.md](./6-review.md) |

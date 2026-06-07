# SHOP-004 切换主题风格 — 架构设计

## 1. 总体方案

**纯前端 CSS 变量方案** — 使用微信小程序支持的 CSS Custom Properties (`var(--xxx)`)，在 `app.wxss` 中定义 4 套主题，通过切换 `<page>` 的 class 来切换主题。主题偏好存储在 `wx.Storage`。

## 2. CSS 变量体系

### 2.1 变量命名规范

```
--color-primary         品牌主色（按钮、标签、选中态、价格文字）
--color-primary-light   主色浅色版（tag 背景）
--color-bg              页面背景色
--color-card            卡片背景色
--color-text            主文字颜色
--color-text-secondary  次要文字颜色
--color-text-muted      辅助文字颜色
--color-border          边框和分割线颜色
--color-border-light    浅色边框
--color-danger          危险/删除红色
--color-success         成功绿色
--color-navbar-bg       导航栏背景色
--color-tab-active      TabBar 选中色
--color-status-pending  订单状态-待付款
--color-status-paid     订单状态-已付款
--color-status-shipped  订单状态-已发货
--color-status-completed 订单状态-已完成
--color-status-cancelled 订单状态-已取消
```

### 2.2 4 套主题配色

```
┌─────────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Variable            │ .theme-orange│ .theme-blue  │ .theme-green │ .theme-dark  │
├─────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ --color-primary     │ #ff5500      │ #1989fa      │ #07c160      │ #d4a853      │
│ --color-primary-lt  │ #fff0f0      │ #e6f7ff      │ #f0fff0      │ #3a3020      │
│ --color-bg          │ #f5f5f5      │ #f5f7fa      │ #f5faf5      │ #1a1a2e      │
│ --color-card        │ #ffffff      │ #ffffff      │ #ffffff      │ #252540      │
│ --color-text        │ #333333      │ #333333      │ #333333      │ #e8e8e8      │
│ --color-text-sc     │ #666666      │ #666666      │ #666666      │ #aaaaaa      │
│ --color-text-muted  │ #999999      │ #999999      │ #999999      │ #777777      │
│ --color-border      │ #eeeeee      │ #e8e8e8      │ #e8e8e8      │ #333344      │
│ --color-border-lt   │ #f0f0f0      │ #f0f0f0      │ #f0f0f0      │ #2a2a3a      │
│ --color-danger      │ #ff4d4f      │ #ff4d4f      │ #ff4d4f      │ #ff6b6b      │
│ --color-success     │ #07c160      │ #07c160      │ #07c160      │ #52c41a      │
│ --color-tab-active  │ #ff5500      │ #1989fa      │ #07c160      │ #d4a853      │
│ --color-navbar-bg   │ #ff5500      │ #1989fa      │ #07c160      │ #1a1a2e      │
│ --color-status-pend │ #fff7e6      │ #e6f7ff      │ #f6ffed      │ #3a3020      │
│ --color-status-paid │ #e6f7ff      │ #e6f7ff      │ #e6f7ff      │ #1a2a3a      │
│ --color-status-ship │ #f0f5ff      │ #f0f5ff      │ #f0f5ff      │ #2a2a3a      │
│ --color-status-comp │ #f6ffed      │ #f6ffed      │ #f6ffed      │ #1a2a1a      │
│ --color-status-canc │ #f5f5f5      │ #f5f5f5      │ #f5f5f5      │ #2a2a2a      │
└─────────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

## 3. 实现方式

### 3.1 app.wxss 结构

```css
/* ===== Theme Variables ===== */
page {
  --color-primary: #ff5500;
  ...
}

.theme-blue page, page.theme-blue {
  --color-primary: #1989fa;
  ...
}

.theme-green page, page.theme-green { ... }
.theme-dark page, page.theme-dark { ... }

/* ===== Global Styles using variables ===== */
.btn { background: var(--color-primary); }
.price { color: var(--color-primary); }
.card { background: var(--color-card); }
...
```

### 3.2 app.js 主题管理

```javascript
// 应用主题
applyTheme: function(theme) {
  // 1. 设置 page class
  var pages = getCurrentPages()
  // 2. 动态设置 navigationBar 颜色
  wx.setNavigationBarColor({ ... })
  // 3. 动态设置 tabBar 样式
  wx.setTabBarStyle({ ... })
  // 4. 存储偏好
  wx.setStorageSync('theme', theme)
  // 5. 更新 globalData
  this.globalData.theme = theme
}
```

### 3.3 数据流

```
┌─────────────────────────────────────────────────────┐
│  用户点击主题按钮                                       │
│       │                                               │
│       ▼                                               │
│  app.setAppTheme(nextTheme)                           │
│       │                                               │
│       ├──→ wx.setStorageSync('theme', nextTheme)     │
│       ├──→ app.globalData.theme = nextTheme          │
│       ├──→ wx.setNavigationBarColor(...)             │
│       ├──→ wx.setTabBarStyle(...)                    │
│       └──→ 遍历页面 setData({ themeClass: ... })      │
│                   │                                   │
│                   ▼                                   │
│              WXSS CSS 变量自动切换 (var(--xxx))        │
│              所有页面颜色即时更新                        │
└─────────────────────────────────────────────────────┘
```

## 4. 与 SHOP-003 (i18n) 的协调

两个功能都涉及：
- `app.js` globalData 扩展（`lang` + `theme`）
- `pages/index/index` 首页按钮（语言 + 主题并列）
- `getCurrentPages()` 遍历刷新

**合并策略**：
- 在已有的 `app.js` 基础上增加 theme 相关代码
- 首页在语言按钮旁增加主题按钮
- 共用 `refreshAllPages` 模式的改进版

## 5. 后端变更

**无**。

## 6. 安全与风险

| 风险 | 缓解 |
|------|------|
| CSS 变量不兼容旧设备 | 微信基础库 2.9.0+（2019年）已支持，覆盖率 >99% |
| 暗色主题门槛色值不协调 | `--color-border`, `--color-card` 等专门为暗色设计了值 |
| 主题切换影响第三方组件 | 无第三方 UI 组件，全部自定义样式 |

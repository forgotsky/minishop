# SHOP-004 切换主题风格 — Story 拆分

## 概述

| 字段 | 值 |
|------|-----|
| Story Key | SHOP-004 |
| 需求 | 切换主题风格 |
| 总预估工时 | **M (5-7h)** |
| 涉及文件数 | **15+ 个**（1 新建 + 14+ 修改） |

---

## Story 拆分

### ST-004-01: 创建主题 CSS 变量系统 `P0`

| 字段 | 值 |
|------|-----|
| 优先级 | **P0** — 基础设施 |
| 工时 | **S (1h)** |
| 前端任务 | 修改 `app.wxss`，定义 4 套主题变量 |

**具体工作**：
- 提取当前所有硬编码色值为 CSS 变量名
- 定义变量命名规范：`--color-primary`, `--color-bg`, `--color-card`, `--color-text`, `--color-text-secondary`, `--color-border`, `--color-danger`, `--color-success` 等
- 每套主题一套变量值：`.theme-orange` / `.theme-blue` / `.theme-green` / `.theme-dark`
- 所有全局样式使用 `var(--xxx)` 引用

**4 套主题配色方案**：

| 变量 | 经典橙 | 深海蓝 | 自然绿 | 暗夜黑 |
|------|--------|--------|--------|--------|
| `--color-primary` | #ff5500 | #1989fa | #07c160 | #d4a853 |
| `--color-bg` | #f5f5f5 | #f5f7fa | #f5faf5 | #1a1a2e |
| `--color-card` | #fff | #fff | #fff | #252540 |
| `--color-text` | #333 | #333 | #333 | #e8e8e8 |
| `--color-text-secondary` | #666 | #666 | #666 | #aaa |
| `--color-text-muted` | #999 | #999 | #999 | #777 |
| `--color-border` | #eee | #e8e8e8 | #e8e8e8 | #333 |
| `--color-danger` | #ff4d4f | #ff4d4f | #ff4d4f | #ff6b6b |
| `--color-success` | #07c160 | #07c160 | #07c160 | #52c41a |
| `--color-tag-bg` | #fff0f0 | #e6f7ff | #f0fff0 | #3a3020 |

---

### ST-004-02: app.js 主题初始化 `P1`

| 字段 | 值 |
|------|-----|
| 优先级 | **P1** |
| 工时 | **S (0.5h)** |
| 前端任务 | 修改 `app.js` |

**具体工作**：
- `onLaunch` 中从 Storage 读取 `theme` 偏好
- 默认 'orange'
- 实现 `applyTheme(theme)` — 设置页面 class + `wx.setNavigationBarColor()` + `wx.setTabBarStyle()`
- `app.globalData.theme` 全局可访问
- 提供给页面的 `setAppTheme(theme)` 切换方法

---

### ST-004-03: 页面 WXSS 变量替换 `P1`

| 字段 | 值 |
|------|-----|
| 优先级 | **P1** |
| 工时 | **M (2h)** |
| 前端任务 | 修改所有页面的 `.wxss` 文件 |

**具体工作**：
- 每页 `*.wxss` 中的硬编码色值替换为 `var(--color-xxx)`
- 涉及的色值类型：
  - Primary: `#ff5500` → `var(--color-primary)`
  - Background: `#f5f5f5` → `var(--color-bg)`
  - Card: `#fff` → `var(--color-card)`
  - Text: `#333` → `var(--color-text)`
  - Text secondary: `#666` → `var(--color-text-secondary)`
  - Text muted: `#999` → `var(--color-text-muted)`
  - Border: `#eee`, `#f0f0f0` → `var(--color-border)`
  - Danger: `#ff4d4f` → `var(--color-danger)`
  - Success: `#07c160` → `var(--color-success)`

**涉及文件**：
- `app.wxss`
- `pages/index/index.wxss`
- `pages/product/product.wxss`
- `pages/cart/cart.wxss`
- `pages/checkout/checkout.wxss`
- `pages/order/order.wxss`
- `pages/order-detail/order-detail.wxss`
- `pages/coupon/coupon.wxss`
- `pages/address/address.wxss`
- `pages/address-edit/address-edit.wxss`

---

### ST-004-04: 主题切换 UI `P2`

| 字段 | 值 |
|------|-----|
| 优先级 | **P2** |
| 工时 | **S (0.5h)** |
| 前端任务 | 修改 `pages/index/index.*` |

**具体工作**：
- 首页增加主题切换按钮（与语言切换按钮并列）
- 点击循环切换：橙→蓝→绿→暗→橙
- 显示当前主题图标/颜色指示器
- 调用 `app.setAppTheme()` 全局更新

---

### ST-004-05: navigationBar + tabBar 动态更新 `P2`

| 字段 | 值 |
|------|-----|
| 优先级 | **P2** |
| 工时 | **S (0.5h)** |
| 前端任务 | 修改 `app.js` `applyTheme` |

**具体工作**：
- `wx.setNavigationBarColor()` 设置 navbar 前景/背景色
- `wx.setTabBarStyle()` 设置 tabBar 颜色
- 暗色主题时 navbar textStyle 为 'white'，light 主题为 'white'（保持 navbar 白色文字）

---

## 推荐实施顺序

```
ST-004-01 (CSS 变量) → ST-004-03 (页面替换) → ST-004-02 (app 初始化)
→ ST-004-05 (nav/tab bar) → ST-004-04 (切换 UI)
```

所有 stories 由 **一个 miniprogram-dev 完成**，无需后端或 K8s 变更。

# SHOP-004: 切换主题风格

## 概述

为 MiniShop 微信小程序添加 4 套视觉主题切换：经典橙、深海蓝、自然绿、暗夜黑。一键切换，即时生效，偏好持久化。

## 技术方案

- **CSS Custom Properties** — 29 个 CSS 变量定义在 `app.wxss`
- **view-based 主题 class** — 每个页面根 view 添加 `theme-xxx` class
- **WeChat API** — `wx.setNavigationBarColor()` + `wx.setTabBarStyle()` 更新导航和标签栏

## 4 套主题

| 主题 | class | 主色 | 背景 | 风格 |
|------|-------|------|------|------|
| 经典橙 | `theme-orange` | #ff5500 | #f5f5f5 | 原风格 |
| 深海蓝 | `theme-blue` | #1989fa | #f5f7fa | 清新 |
| 自然绿 | `theme-green` | #07c160 | #f5faf5 | 柔和 |
| 暗夜黑 | `theme-dark` | #d4a853 | #1a1a2e | 护眼暗色 |

## 文件变更

| 文件 | 变更 |
|------|------|
| `app.wxss` | CSS 变量系统 + 4 套主题定义 |
| `app.js` | `applyTheme()` / `cycleTheme()` / THEME_CONFIG |
| `pages/**/**.wxss` | 硬编码色值 → `var(--xxx)` |
| `pages/**/**.wxml` | 根 view 加 `{{_theme}}` |  
| `pages/**/**.js` | data 加 `_theme` 初始化 |
| `pages/index/` | 主题切换按钮 + `onSwitchTheme()` |

## 如何使用

```javascript
// 切换主题
app.cycleTheme()  // 循环切换 橙→蓝→绿→暗→橙

// 应用指定主题
app.applyTheme('dark')

// 在页面 onLoad/onShow 初始化
this.setData({ _theme: 'theme-' + (app.globalData.theme || 'orange') })
```

## 测试

- 4 套主题 29 变量完整 ✅
- 10 个 WXSS 文件全部使用 CSS 变量 ✅
- `?.`/`??` 0 违规 ✅

## 详细文档

| 文档 | 路径 |
|------|------|
| URS | [1-urs.md](./1-urs.md) |
| Story 拆分 | [2-story.md](./2-story.md) |
| 架构设计 | [3-architecture.md](./3-architecture.md) |
| 测试报告 | [5-tests.md](./5-tests.md) |
| Code Review | [6-review.md](./6-review.md) |

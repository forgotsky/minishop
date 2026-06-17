# SHOP-004 切换主题风格 — 用户需求规格说明书 (URS)

## 1. 功能概述 (Feature Summary)

为 MiniShop 微信商城小程序添加多主题切换功能，用户可以一键切换应用的视觉风格（配色方案）。提供 4 种预设主题：经典橙（默认）、深海蓝、自然绿、暗夜黑。主题切换即时生效，偏好自动持久化。

**目标用户**：
- 对视觉风格有偏好的用户（如暗色模式爱好者）
- 在不同环境下使用小程序的用户（夜间/强光）
- 希望个性化应用外观的用户

## 2. 用户故事 (User Stories)

| # | 角色 | 想做什么 | 以便 |
|---|------|---------|------|
| US-01 | 普通用户 | 在首页切换主题（橙/蓝/绿/暗色） | 根据个人喜好定制应用外观 |
| US-02 | 夜间用户 | 切换到暗色主题 | 在暗光环境下使用不刺眼 |
| US-03 | 回访用户 | 下次打开小程序时保持上次选择的主题 | 无需每次重新设置 |

## 3. 验收标准 (Acceptance Criteria)

### AC-01: 主题切换入口
- **Given** 用户在首页
- **When** 用户点击主题切换按钮
- **Then** 应依次循环切换：橙 → 蓝 → 绿 → 暗 → 橙

### AC-02: 全页面配色更新
- **Given** 用户切换到蓝色主题
- **When** 用户浏览所有页面
- **Then** 所有 UI 元素的品牌色（按钮、标签、导航栏、价格、选中态、边框等）应以蓝色显示

### AC-03: 暗色主题
- **Given** 用户切换到暗色主题
- **When** 用户浏览任意页面
- **Then** 页面背景应为深色，卡片为暗灰色，文字为浅色，按钮保持品牌金色调

### AC-04: 主题持久化
- **Given** 用户上次选择了暗色主题
- **When** 关闭小程序后重新打开
- **Then** 应自动加载暗色主题

### AC-05: 默认主题
- **Given** 首次使用（无主题偏好记录）
- **When** 打开小程序
- **Then** 默认显示经典橙主题

## 4. 范围 (Scope)

### 包含 (In Scope)

| 项目 | 说明 |
|------|------|
| 4 种预设主题 | 经典橙 (Orange)、深海蓝 (Blue)、自然绿 (Green)、暗夜黑 (Dark) |
| 主题 CSS 变量系统 | 在 app.wxss 定义主题色变量 |
| 首页主题切换按钮 | 与语言切换按钮并列 |
| 主题偏好本地存储 | `wx.setStorageSync('theme', 'orange'/'blue'/'green'/'dark')` |
| navigationBar 动态颜色 | `wx.setNavigationBarColor()` 跟随主题变化 |
| tabBar 动态样式 | `wx.setTabBarStyle()` 跟随更新 |
| 所有页面颜色统一更新 | 按钮、标签、价格、状态指示器、边框等 |

### 不包含 (Out of Scope)

| 项目 | 说明 |
|------|------|
| 自定义主题编辑器 | 不支持用户自由选择任意颜色 |
| 后台主题配置 | 不在后端存储用户主题偏好 |
| 按时间段自动切换 | 不实现白天/夜晚自动检测 |
| 字体切换 | 仅颜色变化，不涉及字体 |

## 5. 依赖关系 (Dependencies)

### 前端依赖
- `app.wxss` — 增加 CSS 变量，每种主题一套变量值
- `app.js` — 初始化主题，增加 `setAppTheme()`、`applyTheme()` 方法
- `app.json` — navigationBar 颜色需动态更新
- `utils/i18n.js` — 新增主题相关翻译 key（可选）
- `pages/index/index.*` — 增加主题切换按钮
- 所有 WXSS 文件 — 将硬编码颜色替换为 CSS 变量引用

### 后端依赖
- **无需后端变更**

### 文件清单

| 文件 | 变更类型 |
|------|----------|
| `wechat-miniprogram/app.wxss` | **大量修改** — CSS 变量 + 4 套主题定义 |
| `wechat-miniprogram/app.js` | 修改 — 主题初始化 + 切换逻辑 |
| `wechat-miniprogram/app.json` | 可能修改（navigationBar 配置） |
| `wechat-miniprogram/pages/index/index.wxml` | 修改 — 增加主题切换按钮 |
| `wechat-miniprogram/pages/index/index.js` | 修改 — 主题切换 handler |
| `wechat-miniprogram/pages/*/**.wxss` | 修改 — 硬编码色值改为 CSS 变量 |

## 6. 技术约束 (Technical Constraints)

- **微信小程序 CSS 变量**：基础库 2.9.0+ 支持 `var(--xxx)` 语法（现代微信版本均支持）
- **动态 navigationBar**：`wx.setNavigationBarColor()` 需单独调用
- **动态 tabBar**：`wx.setTabBarStyle()` 需单独调用
- **`?.` / `??` 禁止使用**

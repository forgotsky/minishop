# SHOP-003 中英文双语切换 — 用户需求规格说明书 (URS)

## 1. 功能概述 (Feature Summary)

为 MiniShop 微信商城小程序添加中英文双语切换功能，允许用户在中文与英文之间自由切换 UI 语言。该功能通过前端语言包（i18n）实现，无需后端翻译服务，切换即时生效，语言偏好持久化存储。

**目标用户**：
- 海外华人用户（习惯英文界面）
- 在中国的外籍人士和游客
- 偏好英文界面的国内年轻用户
- 需要中英文对照使用的跨境电商场景

## 2. 用户故事 (User Stories)

| # | 角色 | 想做什么 | 以便 |
|---|------|---------|------|
| US-01 | 普通用户 | 在首页顶部或"我的"页面一键切换中/英文 | 无需复杂设置即可切换语言，提升使用体验 |
| US-02 | 国际用户 | 看到所有页面（商品、购物车、下单、订单、地址、优惠券）的英文翻译 | 不受中文障碍影响完成购物流程 |
| US-03 | 双语用户 | 切换语言后不需要重新登录或刷新数据 | 购物流程不中断，体验流畅 |
| US-04 | 回访用户 | 下次打开小程序时自动显示上次选择的语言 | 无需每次重新设置语言偏好 |

## 3. 验收标准 (Acceptance Criteria)

### AC-01: 语言切换入口
- **Given** 用户已登录 MiniShop
- **When** 用户在首页导航栏或设置区域点击语言切换按钮
- **Then** 按钮应显示当前语言（"中" / "EN"），点击后在两种语言间切换

### AC-02: 全页面翻译覆盖
- **Given** 用户切换到英文
- **When** 用户浏览所有页面（首页、商品详情、购物车、下单、订单列表、订单详情、优惠券、地址管理、地址编辑）
- **Then** 所有 UI 文本（按钮、标签、提示、错误信息、占位符）应以英文显示

### AC-03: 即时切换
- **Given** 用户正在浏览某个页面（如下单页）
- **When** 用户切换语言
- **Then** 当前页面文本应立即更新为新语言，无需页面刷新或重新加载数据

### AC-04: 语言偏好持久化
- **Given** 用户上一次选择了英文
- **When** 用户关闭小程序后再次打开
- **Then** 小程序应自动加载英文界面

### AC-05: 默认语言
- **Given** 用户是首次使用（无语言偏好记录）
- **When** 用户打开小程序
- **Then** 默认显示中文界面

### AC-06: 后端消息国际化
- **Given** 用户使用英文界面
- **When** 后端返回错误消息或提示信息
- **Then** 前端应能以英文显示对应的消息（通过前端本地映射或请求头传递语言偏好）

## 4. 范围 (Scope)

### 包含 (In Scope)

| 项目 | 说明 |
|------|------|
| 语言切换 UI 组件 | 导航栏或"我的"页面的语言切换按钮 |
| 中文简体 + 英文 | 两种语言，单一语言包文件 |
| 全页面 WXML 文本翻译 | 所有 9 个页面的 UI 文本 |
| JS 中的状态标签翻译 | 订单状态、优惠券状态等枚举文本 |
| Toast/提示消息翻译 | `wx.showToast` 中的文字 |
| TabBar 文字翻译 | 底部导航栏（如适用） |
| 语言偏好本地存储 | `wx.setStorageSync('lang', 'zh'/'en')` |
| globalData 语言状态 | `app.globalData.lang` 全局可访问 |

### 不包含 (Out of Scope)

| 项目 | 说明 |
|------|------|
| 自动检测设备语言 | 不根据系统语言自动切换 |
| 服务端翻译内容 | 商品名称、描述等数据库内容不做翻译 |
| RTL 语言支持 | 不支持阿拉伯语等从右到左的语言 |
| 第三种语言 | 仅中英双语，不考虑扩展性 |
| 后端语言偏好存储 | 不在 User 表增加 language 字段（纯前端处理） |
| 字体切换 | 中英文字体不做区分 |

## 5. 依赖关系 (Dependencies)

### 前端依赖
- `app.js` — 增加 `globalData.lang`，启动时从 Storage 读取
- `utils/i18n.js` — 新建语言包模块，提供 `t(key)` 翻译函数
- 所有 9 个页面的 WXML + JS 文件 — 使用 `{{t('key')}}` 或 data binding 方式引入翻译文本
- 所有 `wx.showToast` 调用 — 使用翻译函数

### 后端依赖
- **无需后端变更** — 语言切换为纯前端功能
- 可选的改进：后端支持 `Accept-Language` 请求头，前端在 `api.js` 的请求头中加入当前语言偏好，后端返回对应语言的错误消息

### 文件清单

| 文件 | 变更类型 |
|------|----------|
| `wechat-miniprogram/utils/i18n.js` | **新建** |
| `wechat-miniprogram/app.js` | 修改 — 初始化语言 |
| `wechat-miniprogram/utils/api.js` | 可能修改 — 请求头加语言 |
| `wechat-miniprogram/pages/index/index.wxml` | 修改 — 替换硬编码文本 |
| `wechat-miniprogram/pages/index/index.js` | 修改 — 引入 i18n |
| `wechat-miniprogram/pages/product/product.wxml` | 修改 |
| `wechat-miniprogram/pages/product/product.js` | 修改 |
| `wechat-miniprogram/pages/cart/cart.wxml` | 修改 |
| `wechat-miniprogram/pages/cart/cart.js` | 修改 |
| `wechat-miniprogram/pages/checkout/checkout.wxml` | 修改 |
| `wechat-miniprogram/pages/checkout/checkout.js` | 修改 |
| `wechat-miniprogram/pages/order/order.wxml` | 修改 |
| `wechat-miniprogram/pages/order/order.js` | 修改 |
| `wechat-miniprogram/pages/order-detail/order-detail.wxml` | 修改 |
| `wechat-miniprogram/pages/order-detail/order-detail.js` | 修改 |
| `wechat-miniprogram/pages/coupon/coupon.wxml` | 修改 |
| `wechat-miniprogram/pages/coupon/coupon.js` | 修改 |
| `wechat-miniprogram/pages/address/address.wxml` | 修改 |
| `wechat-miniprogram/pages/address/address.js` | 修改 |
| `wechat-miniprogram/pages/address-edit/address-edit.wxml` | 修改 |
| `wechat-miniprogram/pages/address-edit/address-edit.js` | 修改 |

## 6. 技术约束 (Technical Constraints)

- **禁止 `?.` 可选链** — 微信小程序不支持
- **禁止 `??` 空值合并** — 微信小程序不支持
- **WXS 不支持 ES6 语法** — 如需 WXS 辅助函数，仅用 ES5
- **`wx.setStorageSync` 有 10MB 限制** — 语言包体积远小于限制
- **页面 data 响应式更新** — 语言切换后需 `setData` 触发 UI 重渲染

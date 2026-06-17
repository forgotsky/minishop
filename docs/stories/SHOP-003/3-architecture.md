# SHOP-003 中英文双语切换 — 架构设计

## 1. 总体方案

**纯前端方案** — 语言包定义在 `utils/i18n.js`，各页面通过 `getApp().globalData.lang` 获取当前语言，语言偏好持久化在微信本地 Storage。无需后端变更。

---

## 2. i18n 模块设计 (`utils/i18n.js`)

### 2.1 语言包结构

```
utils/i18n.js
├── texts = { zh: {...}, en: {...} }  ← 语言包对象
├── t(key, lang?)                    ← 翻译函数（JS 中使用）
├── setLang(lang)                    ← 切换语言
├── getLang()                        ← 读取当前语言
└── getAllTexts(lang?)               ← 返回语言包全对象（WXML 中使用）
```

### 2.2 翻译 Key 命名规范

使用点分命名：`page.section.label`

```
search.placeholder        → "搜索商品..." / "Search products..."
index.all                 → "全部" / "All"
cart.empty               → "购物车是空的" / "Your cart is empty"
order.status.pending     → "待付款" / "Pending Payment"
address.form.fullName    → "姓名" / "Full Name"
toast.addedToCart        → "已加入购物车" / "Added to cart"
```

### 2.3 API 签名

```javascript
// JS 中使用
const { t, getAllTexts } = require('../../utils/i18n')
// t('cart.empty') → "购物车是空的" or "Your cart is empty"

// WXML 中使用
// page.js: this.setData({ t: getAllTexts() })
// page.wxml: <text>{{t.cart.empty}}</text>
```

### 2.4 兼容性保障

```javascript
// ❌ 禁止使用（微信小程序不支持）
const lang = wx.getStorageSync('lang') ?? 'zh'  // no
const key = obj?.prop                             // no

// ✅ 正确写法
var lang = wx.getStorageSync('lang') || 'zh'
var key = (obj || {}).prop
```

---

## 3. 数据流

```
┌─────────────────────────────────────────────────────────┐
│  用户点击语言切换按钮                                      │
│       │                                                  │
│       ▼                                                  │
│  app.setAppLang(newLang)                                │
│       │                                                  │
│       ├──→ wx.setStorageSync('lang', newLang)           │
│       ├──→ app.globalData.lang = newLang                │
│       └──→ 当前页面 onShow() → setData({ t: texts })     │
│                   │                                      │
│                   ▼                                      │
│              WXML 自动更新所有 {{t.xxx}} 绑定文本          │
└─────────────────────────────────────────────────────────┘
```

### 启动流程

```
小程序启动 (onLaunch)
  → getLang() 读取 wx.getStorageSync('lang')
  → 默认 'zh'（无记录时）
  → 设置 app.globalData.lang
  → 各页面 onLoad/onShow 时调用 getAllTexts(app.globalData.lang)
  → setData({ t: texts })
  → WXML 渲染 {{t.key}}
```

### 切换流程

```
用户点击切换
  → app.setAppLang(lang === 'zh' ? 'en' : 'zh')
  → Storage 更新
  → app.globalData.lang 更新
  → 当前页面 setData({ t: getAllTexts() })
  → UI 即时更新（无需刷新数据）
```

---

## 4. 前端组件树

```
app.js                          ← +globalData.lang, +setAppLang()
├── utils/i18n.js               ← [新建] 语言包 + 翻译函数
├── utils/api.js                ← 无变更（纯前端 i18n）
├── pages/
│   ├── index/                  ← 首页 + 语言切换按钮入口
│   │   ├── index.wxml          ← 替换硬编码文本为 {{t.xxx}}
│   │   └── index.js            ← onShow 引入 i18n
│   ├── product/                ← 商品详情
│   │   ├── product.wxml
│   │   └── product.js
│   ├── cart/                   ← 购物车
│   │   ├── cart.wxml
│   │   └── cart.js
│   ├── checkout/               ← 下单
│   │   ├── checkout.wxml
│   │   └── checkout.js
│   ├── order/                  ← 订单列表
│   │   ├── order.wxml
│   │   └── order.js            ← STATUS_LABELS 改为从 i18n 读取
│   ├── order-detail/           ← 订单详情
│   │   ├── order-detail.wxml
│   │   └── order-detail.js     ← STATUS_LABELS + 所有 showToast/showModal 文本
│   ├── coupon/                 ← 优惠券
│   │   ├── coupon.wxml
│   │   └── coupon.js
│   ├── address/                ← 地址列表
│   │   ├── address.wxml
│   │   └── address.js
│   └── address-edit/           ← 地址编辑
│       ├── address-edit.wxml
│       └── address-edit.js
```

---

## 5. 后端变更

**无**。此功能为纯前端实现，后端 API 不需要任何修改。

将来可选改进（不在范围）：
- 后端 `User` 表增加 `language` 字段持久化语言偏好
- 后端错误消息根据 `Accept-Language` 头返回对应语言
- 商品名称/描述多语言字段

---

## 6. 存储设计

| 存储位置 | Key | 值 | 说明 |
|----------|-----|-----|------|
| `wx.Storage` | `lang` | `"zh"` 或 `"en"` | 持久化用户语言偏好 |

---

## 7. 安全考虑

- 语言包为客户端静态数据，**不存在注入风险**
- 无用户输入参与翻译拼接
- 无需后端授权检查
- Storage 读写为微信标准 API，不涉及敏感数据

---

## 8. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 遗漏某个页面的翻译 | 翻译 key 不匹配时降级显示 key 名本身（或默认中文），不会崩溃 |
| 语言包过大影响加载 | 整个语言包预估 < 5KB，可忽略 |
| 切换语言后页面闪烁 | `setData` 是同步更新，不会闪烁 |

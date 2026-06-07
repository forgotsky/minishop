# SHOP-003 中英文双语切换 — Story 拆分

## 概述

| 字段 | 值 |
|------|-----|
| Story Key | SHOP-003 |
| 需求 | 中英文双语切换 |
| 总预估工时 | **M (4-6h)** |
| 涉及文件数 | **20 个**（1 新建 + 19 修改） |

---

## Story 拆分

### ST-003-01: 创建 i18n 语言包模块 `P0`

| 字段 | 值 |
|------|-----|
| 优先级 | **P0** — 基础设施，所有后续 story 依赖此模块 |
| 工时 | **S (1h)** |
| 前端任务 | 新建 `utils/i18n.js` |
| 后端任务 | 无 |

**具体工作**：
- 新建 `wechat-miniprogram/utils/i18n.js`
- 定义 `zh` 和 `en` 两个语言包对象，包含所有 UI 文本的 key-value 映射
- 实现 `t(key)` 函数，从当前语言包查找翻译
- 实现 `setLang(lang)` 函数，切换语言并持久化到 `wx.setStorageSync('lang', lang)`
- 实现 `getLang()` 函数，从 Storage 读取（默认 `'zh'`）
- 实现 `getAllTexts()` 函数，返回当前语言的所有文本对象供 WXML 使用

**语言包含的 key（根据现有代码统计）：**

| 分类 | Key 示例 | 中文 | English |
|------|----------|------|---------|
| 通用 | loading, noData, confirm, cancel | 加载中..., 暂无数据, 确认, 取消 | Loading..., No data, Confirm, Cancel |
| 搜索 | searchPlaceholder, searchBtn | Search products..., 搜索 | (already English) |
| 首页 | all, sold, loadMore, empty | 全部, X sold, 加载更多, 暂无商品 | All, X sold, Load more, No products |
| 商品详情 | addToCart, buyNow, stock | 加入购物车, 立即购买, 库存 | Add to Cart, Buy Now, Stock |
| 购物车 | cartEmpty, all, total, checkout, del, removeItem | 购物车是空的, 全选, 合计, 去结算, 删除, 移除？ | Cart empty, All, Total, Checkout, Del, Remove? |
| 下单 | deliveryAddress, new, noAddress, items, coupon, orderSummary, subtotal, discount, delivery, total, placeOrder, selectAddress, orderPlaced, tapSelectCoupon, noCoupons | 收货地址, +新地址, 暂无地址, 商品, 优惠券, 订单摘要, 小计, 优惠, 运费, 合计, 提交订单, 请选择地址, 下单成功, 点击选择优惠券, 暂无可用优惠券 | ... |
| 订单 | orderNo, itemCount, totalAmount, noOrders, noMore, tabs.all/pending/paid/shipped/delivered/completed/cancelled | 订单号, 共X件商品, 实付金额, 暂无订单, 没有更多了, 全部/待付款/待发货/待收货/已完成/已取消 | ... |
| 订单详情 | 订单号, 下单时间, 支付时间, 收货地址, 商品清单, 价格明细, 商品总额, 运费, 实付金额, 物流信息, 立即支付, 取消订单, 确认收货, 查看物流, 支付成功, 支付失败, 已取消, 已确认收货, 暂无物流信息 | ... | ... |
| 优惠券 | myCoupons, getMore, noCoupons, claim, claiming, claimed, noMinSpend, unused, used, expired | 我的优惠券, 领取更多, 暂无优惠券, 领取, 领取中..., 已领取, 无门槛, 未使用, 已使用, 已过期 | ... |
| 地址 | noAddress, addAddress, default, del, deleteConfirm, fillRequired, saved, saveFailed | 暂无地址, 添加地址, 默认, 删除, 确定删除？, 请填写必填项, 已保存, 保存失败 | ... |
| 地址编辑 | fullName, phone, province, city, district, street, zipCode, isDefault, save, update | 姓名*, 电话*, 省*, 市*, 区*, 街道*, 邮编, 默认地址, 保存, 更新 | ... |

---

### ST-003-02: app.js 全局语言初始化 `P1`

| 字段 | 值 |
|------|-----|
| 优先级 | **P1** — 页面翻译依赖全局语言状态 |
| 工时 | **S (0.5h)** |
| 前端任务 | 修改 `app.js` |
| 后端任务 | 无 |

**具体工作**：
- `app.js` 的 `onLaunch` 中从 Storage 读取语言偏好
- 设置 `this.globalData.lang = 'zh'` 或 `'en'`
- 暴露 `app.setAppLang(lang)` 方法供页面调用
- 每次切换后刷新 tabBar 文本

---

### ST-003-03: 首页 + 商品详情页翻译 `P1`

| 字段 | 值 |
|------|-----|
| 优先级 | **P1** |
| 工时 | **S (0.5h)** |
| 前端任务 | 修改 `pages/index/` + `pages/product/` |
| 后端任务 | 无 |

**具体工作**：
- `index.wxml` 将硬编码文本替换为 `{{t.searchPlaceholder}}` 等
- `index.js` 引入 i18n，`onShow` 时设置 `t` 对象
- `product.wxml` 翻译按钮文本
- `product.js` 翻译 Toast 消息

---

### ST-003-04: 购物车 + 下单页翻译 `P1`

| 字段 | 值 |
|------|-----|
| 优先级 | **P1** |
| 工时 | **S (0.5h)** |
| 前端任务 | 修改 `pages/cart/` + `pages/checkout/` |
| 后端任务 | 无 |

---

### ST-003-05: 订单列表 + 订单详情页翻译 `P1`

| 字段 | 值 |
|------|-----|
| 优先级 | **P1** |
| 工时 | **S (1h)** |
| 前端任务 | 修改 `pages/order/` + `pages/order-detail/` |
| 后端任务 | 无 |

**注意**：这两页有最多的中文硬编码，包括 STATUS_LABELS 和 `wx.showModal` 文本。

---

### ST-003-06: 优惠券 + 地址页翻译 `P2`

| 字段 | 值 |
|------|-----|
| 优先级 | **P2** |
| 工时 | **S (0.5h)** |
| 前端任务 | 修改 `pages/coupon/` + `pages/address/` + `pages/address-edit/` |
| 后端任务 | 无 |

---

### ST-003-07: 语言切换 UI 组件 `P2`

| 字段 | 值 |
|------|-----|
| 优先级 | **P2** |
| 工时 | **S (0.5h)** |
| 前端任务 | 在首页导航栏增加语言切换按钮 |
| 后端任务 | 无 |

**具体工作**：
- 首页或全局添加语言切换入口（如 "中/EN" 按钮）
- 点击后调用 `app.setAppLang()` 切换到另一种语言
- 当前页面 `onShow` 重新设置 `t` 对象

---

### ST-003-08: 集成测试 `P2`

| 字段 | 值 |
|------|-----|
| 优先级 | **P2** |
| 工时 | **S (0.5h)** |
| 前端任务 | 验证所有页面中英文切换正常 |
| 后端任务 | 无（纯前端） |

---

## 推荐实施顺序

```
ST-003-01 (i18n 模块) → ST-003-02 (app.js 初始化)
→ ST-003-03 (首页+商品) → ST-003-04 (购物车+下单)
→ ST-003-05 (订单) → ST-003-06 (优惠券+地址)
→ ST-003-07 (切换 UI) → ST-003-08 (测试验证)
```

所有 stories 均可由**一个 miniprogram-dev 完成**，无需后端或 K8s 变更。

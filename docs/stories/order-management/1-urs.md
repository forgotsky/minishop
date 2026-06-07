# URS — 订单管理 (order-management)

## 1. Feature Summary

订单管理功能：用户查看、操作订单的完整生命周期管理，包括订单列表、订单详情、订单状态更新、取消订单等核心功能。

## 2. User Stories

### Story 1: 查看订单列表
- **As a** 买家
- **I want** 在订单列表页查看我的所有订单
- **So that** 我可以快速找到需要的订单进行操作

### Story 2: 查看订单详情
- **As a** 买家
- **I want** 点击订单查看详细信息（商品、价格、地址、物流）
- **So that** 我能确认订单内容是否正确

### Story 3: 取消订单
- **As a** 买家
- **I want** 在订单未发货前取消订单
- **So that** 我可以取消错误或不需要的订单

### Story 4: 确认收货
- **As a** 买家
- **I want** 收到货物后确认收货
- **So that** 订单状态更新为已完成

### Story 5: 查看物流
- **As a** 买家
- **I want** 查看订单的物流进度
- **So that** 我知道商品什么时候能收到

## 3. Acceptance Criteria

### AC1: 订单列表
```
Given 用户已登录
When 用户进入订单列表页
Then 显示所有订单（按时间倒序）
And 显示订单状态标签（待付款/待发货/待收货/已完成/已取消）
And 显示订单号、商品图片、金额、时间
```

### AC2: 订单详情
```
Given 用户在订单列表页
When 用户点击某个订单
Then 跳转订单详情页
And 显示：订单号、创建时间、订单状态
And 显示：商品列表（图片、名称、数量、价格）
And 显示：收货地址、联系电话
And 显示：支付信息（支付方式、总金额、运费）
And 显示：操作按钮（取消/确认收货/查看物流）
```

### AC3: 取消订单
```
Given 用户在订单详情页
And 订单状态为"待发货"或之前
When 用户点击"取消订单"按钮
Then 弹出确认对话框
When 用户确认取消
Then 订单状态更新为"已取消"
And 显示取消成功提示
```

### AC4: 确认收货
```
Given 用户在订单详情页
And 订单状态为"待收货"
When 用户点击"确认收货"按钮
Then 弹出确认对话框
When 用户确认
Then 订单状态更新为"已完成"
And 显示确认成功提示
```

### AC5: 物流查询
```
Given 用户在订单详情页
And 订单状态为"待收货"或之后
When 用户点击"查看物流"按钮
Then 显示物流公司名称和运单号
And 显示物流轨迹（时间、地点、状态）
```

## 4. Scope

### In Scope
- 订单列表查询（支持状态筛选）
- 订单详情展示
- 取消订单（待发货前）
- 确认收货
- 物流信息展示

### Out of Scope
- 退款/售后（V2）
- 评价功能（V2）
- 发票开具（V2）
- 订单导出（V2）

## 5. Dependencies

- 后端：`GET /orders`, `GET /orders/{id}`, `PATCH /orders/{id}/status`
- 前端：新建 `pages/order/` 和 `pages/order-detail/`
- 微信 API：`wx.navigateTo`, `wx.showModal`
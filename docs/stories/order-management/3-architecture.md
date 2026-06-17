# Architecture — 订单管理

## API Endpoints

### 1. GET /orders
获取当前用户订单列表

**Request:**
```
Query: status (optional): pending | paid | shipped | delivered | completed | cancelled
       page (optional): int, default 1
       limit (optional): int, default 20
Headers: Authorization: Bearer <token>
```

**Response:**
```json
{
  "orders": [
    {
      "id": "uuid",
      "order_no": "ORD20240607001",
      "status": "paid",
      "total_amount": 299.00,
      "created_at": "2024-06-07T10:00:00Z",
      "items_count": 3,
      "first_item": {
        "name": "商品名称",
        "image": "/static/images/xxx.jpg"
      }
    }
  ],
  "total": 50,
  "page": 1,
  "pages": 3
}
```

### 2. GET /orders/{id}
获取订单详情

**Response:**
```json
{
  "id": "uuid",
  "order_no": "ORD20240607001",
  "status": "paid",
  "created_at": "2024-06-07T10:00:00Z",
  "paid_at": "2024-06-07T10:05:00Z",
  "items": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "name": "商品名称",
      "image": "/static/images/xxx.jpg",
      "price": 99.00,
      "quantity": 2,
      "subtotal": 198.00
    }
  ],
  "shipping_address": {
    "name": "张三",
    "phone": "13800138000",
    "address": "北京市朝阳区xxx"
  },
  "payment": {
    "method": "wechat",
    "total": 299.00,
    "freight": 0.00
  },
  "tracking": {
    "company": "顺丰速运",
    "number": "SF1234567890",
    "status": "shipped",
    "updated_at": "2024-06-08T14:00:00Z"
  }
}
```

### 3. PATCH /orders/{id}/status
更新订单状态

**Request:**
```json
{
  "action": "cancel" | "complete"
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "cancelled" | "completed",
  "updated_at": "2024-06-07T15:00:00Z"
}
```

**Validation:**
- `cancel`: 仅 status=pending/paid 时允许
- `complete`: 仅 status=delivered 时允许

### 4. GET /orders/{id}/tracking
获取物流信息

**Response:**
```json
{
  "company": "顺丰速运",
  "number": "SF1234567890",
  "status": "shipping",
  "traces": [
    {
      "time": "2024-06-08T14:00:00Z",
      "location": "深圳分拨中心",
      "description": "快件已发出，正在运输中"
    },
    {
      "time": "2024-06-07T16:00:00Z",
      "location": "深圳宝安分部",
      "description": "快件已揽收"
    }
  ]
}
```

## Database Changes

### Table: orders
新增字段：
- `status` VARCHAR(20) DEFAULT 'pending' — 订单状态
- `tracking_number` VARCHAR(50) — 物流单号
- `tracking_company` VARCHAR(50) — 物流公司
- `shipped_at` TIMESTAMP — 发货时间
- `delivered_at` TIMESTAMP — 收货时间
- `cancelled_at` TIMESTAMP — 取消时间
- `cancel_reason` TEXT — 取消原因

### Table: order_items
新增字段：
- `product_id` UUID — 关联商品（可为空）

## Frontend Component Tree

```
pages/order/
├── index.wxml          # 订单列表页
│   ├── tabs (状态筛选)
│   └── order-card (订单卡片)
│       ├── order-no
│       ├── status-tag
│       ├── item-preview
│       └── amount
├── index.js            # 列表逻辑
│   ├── onLoad → fetchOrders()
│   ├── onTabsChange → filter by status
│   └── onReachBottom → loadMore()
└── index.wxss          # 样式

pages/order-detail/
├── index.wxml          # 订单详情页
│   ├── order-header (状态、时间)
│   ├── address-block
│   ├── items-list (商品列表)
│   ├── payment-summary
│   ├── tracking-block (物流信息)
│   └── action-bar (操作按钮)
├── index.js            # 详情逻辑
│   ├── onLoad → fetchOrderDetail(id)
│   ├── onCancel → confirm + API
│   └── onConfirmReceive → confirm + API
└── index.wxss          # 样式
```

## Data Flow

```
User Action
    ↓
Frontend (wx.navigateTo / API call)
    ↓
Backend API (FastAPI)
    ↓
Database (PostgreSQL)
    ↓
Response JSON
    ↓
Frontend Render
```

## Security Considerations

1. **Authorization**: 所有接口需要 JWT token，用户只能查看自己的订单
2. **Ownership Check**: 查询订单时验证 `user_id` 匹配
3. **Action Validation**: 状态变更需验证当前状态是否允许该操作
4. **Rate Limiting**: 列表接口加限流防止爬取

## WeChat Compatibility

- 禁止使用 `?.` 可选链 → 用 `|| {}` 替代
- 禁止使用 `??` 空值合并 → 用 `||` 替代
- 页面栈限制 10 层，注意 navigateBack 使用
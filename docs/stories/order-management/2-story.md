# Story Breakdown — 订单管理

## Stories

### Story O-1: 订单列表页
| Field | Value |
|-------|-------|
| Key | O-1 |
| Priority | P0 |
| Effort | M |
| Frontend | `pages/order/` (index.wxml, index.js, index.wxss) |
| Backend | `GET /orders` (query: status, page, limit) |

**Tasks Frontend:**
- 创建 order 页面目录
- 编写 order/index.wxml — 订单列表模板
- 编写 order/index.js — 调用 API 获取订单列表，状态筛选 tabs
- 编写 order/index.wxss — 列表样式

**Tasks Backend:**
- `GET /orders` — 查询用户订单，支持 status 筛选和分页

---

### Story O-2: 订单详情页
| Field | Value |
|-------|-------|
| Key | O-2 |
| Priority | P0 |
| Effort | M |
| Frontend | `pages/order-detail/` |
| Backend | `GET /orders/{id}` |

**Tasks Frontend:**
- 创建 order-detail 页面目录
- 编写 order-detail/index.wxml — 详情展示模板
- 编写 order-detail/index.js — 调用 API 获取订单详情
- 实现取消按钮、确认收货按钮、查看物流按钮

**Tasks Backend:**
- `GET /orders/{id}` — 查询订单详情（含商品、地址、物流）

---

### Story O-3: 取消订单
| Field | Value |
|-------|-------|
| Key | O-3 |
| Priority | P0 |
| Effort | S |
| Frontend | order-detail 页内按钮 |
| Backend | `PATCH /orders/{id}/status` (cancel) |

**Tasks Frontend:**
- 点击取消 → showModal 确认 → 调用取消 API → 刷新详情

**Tasks Backend:**
- `PATCH /orders/{id}/status` — 仅允许待发货状态取消，更新状态为 cancelled

---

### Story O-4: 确认收货
| Field | Value |
|-------|-------|
| Key | O-4 |
| Priority | P0 |
| Effort | S |
| Frontend | order-detail 页内按钮 |
| Backend | `PATCH /orders/{id}/status` (complete) |

**Tasks Frontend:**
- 点击确认收货 → showModal 确认 → 调用 API → 刷新详情

**Tasks Backend:**
- `PATCH /orders/{id}/status` — 仅允许待收货状态确认，更新状态为 completed

---

### Story O-5: 物流查询
| Field | Value |
|-------|-------|
| Key | O-5 |
| Priority | P1 |
| Effort | L |
| Frontend | order-detail 页内物流区块 |
| Backend | `GET /orders/{id}/tracking` |

**Tasks Frontend:**
- 显示物流公司 + 运单号
- 调用物流查询 API 显示物流轨迹

**Tasks Backend:**
- `GET /orders/{id}/tracking` — 返回物流信息（集成第三方快递查询）

---

## Tech Tasks

### Backend
- [ ] Model: Order, OrderItem, Shipping 添加 status, tracking_number 字段
- [ ] Endpoint: `GET /orders` (list with filter)
- [ ] Endpoint: `GET /orders/{id}` (detail)
- [ ] Endpoint: `PATCH /orders/{id}/status` (cancel/complete)
- [ ] Endpoint: `GET /orders/{id}/tracking` (logistics)

### Frontend
- [ ] Pages: `pages/order/` — 订单列表
- [ ] Pages: `pages/order-detail/` — 订单详情
- [ ] API: `utils/api.js` 添加订单相关方法

### K8s
- 无需变更
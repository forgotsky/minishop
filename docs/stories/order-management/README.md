# 订单管理 — order-management

## 功能概述

用户可以查看订单列表、订单详情、取消订单（待发货前）、确认收货、查看物流信息。

## API 接口

### 订单列表
```
GET /api/orders
Query: status (optional), page, page_size
Auth: required
Response: { orders: [...], total, page, pages }
```

### 订单详情
```
GET /api/orders/{id}
Auth: required
Response: OrderDetailOut (含 shipping_address, tracking)
```

### 更新订单状态
```
PATCH /api/orders/{id}/status
Body: { action: "cancel" | "complete" }
Auth: required
- cancel: 仅 pending/paid 状态可取消
- complete: 仅 delivered 状态可确认收货
```

### 物流查询
```
GET /api/orders/{id}/tracking
Auth: required
Response: { company, number, status, traces: [...] }
```

## 前端页面

| 页面 | 文件 | 功能 |
|---|---|---|
| 订单列表 | `pages/order/` | 状态 tab 筛选、分页加载 |
| 订单详情 | `pages/order-detail/` | 详情展示、取消/确认收货/查看物流 |

## 状态流转

```
pending → paid → shipped → delivered → completed
    ↓
 cancelled (pending/paid 时可取消)
```

## 测试命令

```bash
cd backend && pytest tests/test_orders.py -v
```

## 已知限制

- 物流信息需人工通过数据库写入 `tracking_company` / `tracking_number`
- 完整物流轨迹（第三方 API）V2 实现
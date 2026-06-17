# Test Report — order-management

## Summary
- **Total**: 38 tests
- **Passed**: 38
- **Failed**: 0
- **Duration**: ~2s

## Test Breakdown

| Category | Tests | Status |
|---|---|---|
| Order creation | 7 | ✅ |
| Order list (new format) | 2 | ✅ |
| Order detail (address snapshot) | 1 | ✅ |
| Payment flow | 3 | ✅ |
| Coupon application | 4 | ✅ |
| Partial cart checkout | 1 | ✅ |
| Stock deduction | 1 | ✅ |
| Negative tests | 5 | ✅ |
| Cross-user isolation | 6 | ✅ |
| Pagination (updated) | 5 | ✅ |
| Status filter | 1 | ✅ |
| Cancel order | 4 | ✅ |
| Complete order | 2 | ✅ |
| Tracking | 3 | ✅ |

## New Endpoints Tested

- `GET /api/orders?status=X` — ✅ status filter works
- `GET /api/orders/{id}` — ✅ returns shipping_address snapshot
- `PATCH /api/orders/{id}/status` — ✅ cancel/complete actions
- `GET /api/orders/{id}/tracking` — ✅ returns tracking info
- All endpoints enforce user ownership — ✅ 404 on cross-user access
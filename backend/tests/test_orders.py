"""
Tests for order endpoints: create, list, detail, pay, coupon application,
cross-user isolation, stock deduction, and edge cases.
"""

import pytest


# ── Helpers ───────────────────────────────────────────────────────────

async def _create_address(client, headers, suffix=""):
    """Create a test address and return its id."""
    resp = await client.post("/api/addresses", json={
        "full_name": f"Test{suffix}",
        "phone": "13800138000",
        "province": "TestProvince",
        "city": "TestCity",
        "district": "TestDistrict",
        "street": f"123 Test St{suffix}",
    }, headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


async def _add_to_cart_and_get_item_ids(client, headers, items):
    """Add products to cart and return list of cart item ids.
    items: list of (product_id, quantity) tuples.
    """
    ids = []
    for product_id, quantity in items:
        await client.post("/api/cart/items", json={
            "product_id": product_id, "quantity": quantity,
        }, headers=headers)
    cart = await client.get("/api/cart", headers=headers)
    for item in cart.json()["items"]:
        ids.append(item["id"])
    return ids


# ── Basic order tests ─────────────────────────────────────────────────

async def test_create_order_empty_cart(client, auth_headers):
    """POST /api/orders with empty cart → 400."""
    headers = await auth_headers(code="order_empty_test")
    addr_id = await _create_address(client, headers, "Empty")

    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers)
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


async def test_create_order(client, auth_headers):
    """POST /api/orders with cart items → 200, returns order with pending status."""
    headers = await auth_headers(code="order_create_test")

    # Add item to cart
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)

    addr_id = await _create_address(client, headers, "Create")

    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_no"].startswith("ORD")
    assert data["status"] == "pending"
    assert data["total_amount"] > 0
    # 1 item at 49.99 + 5.00 delivery = 54.99
    assert data["payment_amount"] == 54.99


async def test_create_order_with_multiple_products(client, auth_headers):
    """Order with multiple different products calculates total correctly."""
    headers = await auth_headers(code="order_multi_test")

    # Product 1: 49.99 * 2 = 99.98
    # Product 2: 89.00 * 1 = 89.00
    # Total = 188.98, payment = 188.98 + 5.00 = 193.98
    await _add_to_cart_and_get_item_ids(client, headers, [
        (1, 2),
        (2, 1),
    ])
    addr_id = await _create_address(client, headers, "Multi")

    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_amount"] == 188.98
    assert data["payment_amount"] == 193.98
    assert len(data["items"]) == 2


async def test_list_orders(client, auth_headers):
    """GET /api/orders returns a list of the user's orders."""
    headers = await auth_headers(code="order_list_test")

    # Create an order first
    await client.post("/api/cart/items", json={
        "product_id": 2, "quantity": 1,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "List")
    await client.post("/api/orders", json={"address_id": addr_id}, headers=headers)

    resp = await client.get("/api/orders", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["order_no"].startswith("ORD")


async def test_get_order_detail(client, auth_headers):
    """GET /api/orders/{id} returns full order detail with items."""
    headers = await auth_headers(code="order_detail_test")

    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 2,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "Detail")

    create_resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers)
    order_id = create_resp.json()["id"]

    detail = await client.get(f"/api/orders/{order_id}", headers=headers)
    assert detail.status_code == 200
    data = detail.json()
    assert data["id"] == order_id
    assert data["status"] == "pending"
    assert data["delivery_fee"] == 5.0
    assert data["created_at"] is not None
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == 1
    assert data["items"][0]["product_name"] == "Wireless Headphones"
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["product_price"] == 49.99


# ── Payment flow ──────────────────────────────────────────────────────

async def test_pay_order(client, auth_headers):
    """POST /api/orders/{id}/pay transitions status from pending to paid."""
    headers = await auth_headers(code="order_pay_test")

    # Create an order
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "Pay")
    create_resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers)
    order_id = create_resp.json()["id"]

    # Pay
    pay_resp = await client.post(f"/api/orders/{order_id}/pay", headers=headers)
    assert pay_resp.status_code == 200
    assert pay_resp.json()["message"] == "Payment successful"

    # Verify status is now "paid"
    detail = await client.get(f"/api/orders/{order_id}", headers=headers)
    assert detail.json()["status"] == "paid"


async def test_pay_order_already_paid(client, auth_headers):
    """Paying an already-paid order → 400."""
    headers = await auth_headers(code="order_pay_twice_test")

    # Create an order
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "PayTwice")
    create_resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers)
    order_id = create_resp.json()["id"]

    # First payment succeeds
    pay1 = await client.post(f"/api/orders/{order_id}/pay", headers=headers)
    assert pay1.status_code == 200

    # Second payment fails
    pay2 = await client.post(f"/api/orders/{order_id}/pay", headers=headers)
    assert pay2.status_code == 400
    assert "cannot be paid" in pay2.json()["detail"].lower()


async def test_pay_nonexistent_order(client, auth_headers):
    """POST /api/orders/9999/pay → 404."""
    headers = await auth_headers(code="order_pay_404_test")
    resp = await client.post("/api/orders/9999/pay", headers=headers)
    assert resp.status_code == 404


# ── Coupon application ────────────────────────────────────────────────

async def test_create_order_with_full_reduction_coupon(client, auth_headers):
    """Order with a full-reduction coupon applies discount when total >= threshold."""
    headers = await auth_headers(code="order_coupon_fr_test")

    # Claim coupon 1: 满100减20 (threshold=100, value=20)
    claim_resp = await client.post("/api/coupons/1/claim", headers=headers)
    assert claim_resp.status_code == 200
    # Get the UserCoupon id
    user_coupons = await client.get("/api/user/coupons", headers=headers)
    coupon_id = user_coupons.json()[0]["id"]

    # Add product 1 * 3 = 149.97 >= 100 threshold
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 3,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "CouponFR")

    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
        "coupon_id": coupon_id,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_amount"] == 149.97
    assert data["discount_amount"] == 20.0
    # 149.97 - 20 + 5 = 134.97
    assert data["payment_amount"] == 134.97

    # Coupon should now be marked as used
    user_coupons_after = await client.get("/api/user/coupons", headers=headers)
    used_coupon = [c for c in user_coupons_after.json() if c["id"] == coupon_id][0]
    assert used_coupon["status"] == "used"


async def test_create_order_with_coupon_under_threshold(client, auth_headers):
    """Coupon is NOT applied when order total is below the coupon threshold."""
    headers = await auth_headers(code="order_coupon_under_test")

    # Claim coupon 1: 满100减20 (threshold=100)
    await client.post("/api/coupons/1/claim", headers=headers)
    user_coupons = await client.get("/api/user/coupons", headers=headers)
    coupon_id = user_coupons.json()[0]["id"]

    # Add product 1 * 1 = 49.99 < 100 threshold
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "UnderThresh")

    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
        "coupon_id": coupon_id,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Discount should be 0 because threshold not met
    assert data["discount_amount"] == 0.0
    # 49.99 + 5.00 = 54.99
    assert data["payment_amount"] == 54.99

    # Coupon should remain "unused" because the order total (49.99)
    # is below the coupon threshold (100). The coupon is only consumed
    # when the discount is actually applied.
    user_coupons_after = await client.get("/api/user/coupons", headers=headers)
    coupon = [c for c in user_coupons_after.json() if c["id"] == coupon_id][0]
    assert coupon["status"] == "unused"


async def test_create_order_with_discount_coupon(client, auth_headers):
    """Order with a percentage discount coupon applies correctly."""
    headers = await auth_headers(code="order_coupon_disc_test")

    # Claim coupon 3: 电子产品9折券 (type=discount, value=90, meaning 90% → 10% off)
    await client.post("/api/coupons/3/claim", headers=headers)
    user_coupons = await client.get("/api/user/coupons", headers=headers)
    coupon_id = user_coupons.json()[0]["id"]

    # Product 1 (electronics): 49.99 * 1
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "Discount")

    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
        "coupon_id": coupon_id,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # discount = round(49.99 * (1 - 90/100), 2) = round(4.999, 2) = 5.00
    assert data["discount_amount"] == 5.0
    # 49.99 - 5.00 + 5.00 = 49.99
    assert data["payment_amount"] == 49.99


async def test_create_order_with_nonexistent_coupon(client, auth_headers):
    """Passing a non-existent coupon_id simply does not apply any discount."""
    headers = await auth_headers(code="order_coupon_404_test")

    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "BadCoupon")

    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
        "coupon_id": 9999,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # No discount applied because coupon not found
    assert data["discount_amount"] == 0.0
    assert data["payment_amount"] == 54.99


# ── Partial cart checkout ─────────────────────────────────────────────

async def test_create_order_with_specific_items(client, auth_headers):
    """Order with item_ids only checks out selected cart items; rest stays in cart."""
    headers = await auth_headers(code="order_partial_test")

    # Add two different products to cart
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    await client.post("/api/cart/items", json={
        "product_id": 2, "quantity": 1,
    }, headers=headers)

    # Get item ids
    cart = await client.get("/api/cart", headers=headers)
    items = cart.json()["items"]
    assert len(items) == 2
    # Find the item id for product 1
    item_1_id = [it["id"] for it in items if it["product_id"] == 1][0]

    addr_id = await _create_address(client, headers, "Partial")

    # Create order only for product 1
    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
        "item_ids": [item_1_id],
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == 1
    # Only product 1: 49.99 + 5 = 54.99
    assert data["payment_amount"] == 54.99

    # Product 2 should still be in the cart
    cart_after = await client.get("/api/cart", headers=headers)
    remaining = cart_after.json()["items"]
    assert len(remaining) == 1
    assert remaining[0]["product_id"] == 2


# ── Stock deduction & cart clearing ───────────────────────────────────

async def test_create_order_deducts_stock(client, auth_headers):
    """After order creation, product stock is reduced and cart is emptied."""
    headers = await auth_headers(code="order_stock_test")

    # Add product 1 with quantity 3
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 3,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "Stock")

    # Get initial stock (product 1 starts with 120)
    product_before = await client.get("/api/products/1")
    stock_before = product_before.json()["stock"]
    sales_before = product_before.json()["sales_count"]

    # Create order
    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers)
    assert resp.status_code == 200

    # Stock should be reduced by 3
    product_after = await client.get("/api/products/1")
    assert product_after.json()["stock"] == stock_before - 3
    assert product_after.json()["sales_count"] == sales_before + 3

    # Cart should be empty
    cart_after = await client.get("/api/cart", headers=headers)
    assert cart_after.json()["items"] == []
    assert cart_after.json()["total"] == 0


# ── Order fields / creation edge cases ────────────────────────────────

async def test_create_order_with_remark(client, auth_headers):
    """Order with a remark field stores the remark correctly."""
    headers = await auth_headers(code="order_remark_test")

    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    addr_id = await _create_address(client, headers, "Remark")

    resp = await client.post("/api/orders", json={
        "address_id": addr_id,
        "remark": "Please gift-wrap the items",
        "payment_method": "wechat",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["payment_amount"] == 54.99
    # Verify remark was actually persisted and returned
    assert data["remark"] == "Please gift-wrap the items"


# ── Negative tests ────────────────────────────────────────────────────

async def test_create_order_invalid_address(client, auth_headers):
    """POST /api/orders with a non-existent address_id → 400."""
    headers = await auth_headers(code="order_bad_addr_test")

    # Add item to cart
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)

    resp = await client.post("/api/orders", json={
        "address_id": 9999,
    }, headers=headers)
    assert resp.status_code == 400
    assert "address" in resp.json()["detail"].lower()


async def test_get_order_404(client, auth_headers):
    """GET /api/orders/9999 (non-existent) → 404."""
    headers = await auth_headers(code="order_404_test")
    resp = await client.get("/api/orders/9999", headers=headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_order_requires_auth(client):
    """All order endpoints require authentication → 401 without token."""
    # POST /api/orders
    resp = await client.post("/api/orders", json={"address_id": 1})
    assert resp.status_code == 401

    # GET /api/orders
    resp = await client.get("/api/orders")
    assert resp.status_code == 401

    # GET /api/orders/1
    resp = await client.get("/api/orders/1")
    assert resp.status_code == 401

    # POST /api/orders/1/pay
    resp = await client.post("/api/orders/1/pay")
    assert resp.status_code == 401


# ── Cross-user isolation ──────────────────────────────────────────────

async def test_order_cross_user_isolation(client, auth_headers):
    """User B cannot view User A's order."""
    headers_a = await auth_headers(code="order_user_a")
    headers_b = await auth_headers(code="order_user_b")

    # User A creates an order
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers_a)
    addr_id = await _create_address(client, headers_a, "IsoA")
    create_resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers_a)
    order_id = create_resp.json()["id"]

    # User A can see the order
    detail_a = await client.get(f"/api/orders/{order_id}", headers=headers_a)
    assert detail_a.status_code == 200

    # User B cannot see User A's order → 404
    detail_b = await client.get(f"/api/orders/{order_id}", headers=headers_b)
    assert detail_b.status_code == 404


async def test_pay_order_cross_user(client, auth_headers):
    """User B cannot pay User A's order."""
    headers_a = await auth_headers(code="order_pay_iso_a")
    headers_b = await auth_headers(code="order_pay_iso_b")

    # User A creates an order
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers_a)
    addr_id = await _create_address(client, headers_a, "PayIsoA")
    create_resp = await client.post("/api/orders", json={
        "address_id": addr_id,
    }, headers=headers_a)
    order_id = create_resp.json()["id"]

    # User B tries to pay User A's order → 404
    pay_b = await client.post(f"/api/orders/{order_id}/pay", headers=headers_b)
    assert pay_b.status_code == 404

    # User A can still pay it
    pay_a = await client.post(f"/api/orders/{order_id}/pay", headers=headers_a)
    assert pay_a.status_code == 200


async def test_create_order_cross_user_address(client, auth_headers):
    """Using another user's address_id → 400."""
    headers_a = await auth_headers(code="order_addr_iso_a")
    headers_b = await auth_headers(code="order_addr_iso_b")

    # User A creates an address
    addr_a = await _create_address(client, headers_a, "AddrA")

    # User B adds to cart, then tries to use User A's address
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers_b)

    resp = await client.post("/api/orders", json={
        "address_id": addr_a,  # User A's address
    }, headers=headers_b)
    assert resp.status_code == 400
    assert "address" in resp.json()["detail"].lower()


async def test_create_order_cross_user_coupon(client, auth_headers):
    """Using another user's coupon_id → discount not applied."""
    headers_a = await auth_headers(code="order_coupon_iso_a")
    headers_b = await auth_headers(code="order_coupon_iso_b")

    # User A claims a coupon
    await client.post("/api/coupons/1/claim", headers=headers_a)
    user_coupons_a = await client.get("/api/user/coupons", headers=headers_a)
    coupon_id_a = user_coupons_a.json()[0]["id"]

    # User B adds to cart and tries to use User A's coupon
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 3,  # 149.97 >= 100 threshold
    }, headers=headers_b)
    addr_b = await _create_address(client, headers_b, "CouponIsoB")

    resp = await client.post("/api/orders", json={
        "address_id": addr_b,
        "coupon_id": coupon_id_a,  # User A's coupon
    }, headers=headers_b)
    assert resp.status_code == 200
    data = resp.json()
    # Discount should NOT be applied (coupon belongs to User A)
    assert data["discount_amount"] == 0.0
    assert data["payment_amount"] == 154.97  # 149.97 + 5.00, no discount

    # User A's coupon should still be unused
    coupons_a = await client.get("/api/user/coupons", headers=headers_a)
    assert coupons_a.json()[0]["status"] == "unused"


async def test_list_orders_cross_user_isolation(client, auth_headers):
    """GET /api/orders only returns the authenticated user's orders."""
    headers_a = await auth_headers(code="order_list_iso_a")
    headers_b = await auth_headers(code="order_list_iso_b")

    # User A creates an order
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers_a)
    addr_a = await _create_address(client, headers_a, "ListIsoA")
    await client.post("/api/orders", json={"address_id": addr_a}, headers=headers_a)

    # User B's order list is empty
    orders_b = await client.get("/api/orders", headers=headers_b)
    assert orders_b.status_code == 200
    assert orders_b.json() == []

    # User A's order list shows the order
    orders_a = await client.get("/api/orders", headers=headers_a)
    assert len(orders_a.json()) == 1


# ── Pagination tests ─────────────────────────────────────────────────

async def test_list_orders_pagination(client, auth_headers):
    """GET /api/orders supports pagination with page and page_size params."""
    headers = await auth_headers(code="order_page_test")

    # Create 3 orders
    for i in range(3):
        await client.post("/api/cart/items", json={
            "product_id": i + 1, "quantity": 1,
        }, headers=headers)
        addr_id = await _create_address(client, headers, f"Page{i}")
        resp = await client.post("/api/orders", json={
            "address_id": addr_id,
        }, headers=headers)
        assert resp.status_code == 200

    # Page 1, size 2 → 2 items
    resp = await client.get("/api/orders", headers=headers, params={
        "page": 1, "page_size": 2,
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Page 2, size 2 → 1 item
    resp = await client.get("/api/orders", headers=headers, params={
        "page": 2, "page_size": 2,
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Default pagination returns all (page=1, page_size=10)
    resp = await client.get("/api/orders", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_list_orders_pagination_invalid_page(client, auth_headers):
    """GET /api/orders with page=0 → 422 (ge=1 validation)."""
    headers = await auth_headers(code="order_page_inv_test")
    resp = await client.get("/api/orders", headers=headers, params={
        "page": 0,
    })
    assert resp.status_code == 422


async def test_list_orders_pagination_invalid_page_size_zero(client, auth_headers):
    """GET /api/orders with page_size=0 → 422 (ge=1 validation)."""
    headers = await auth_headers(code="order_psize0_test")
    resp = await client.get("/api/orders", headers=headers, params={
        "page_size": 0,
    })
    assert resp.status_code == 422


async def test_list_orders_pagination_invalid_page_size_51(client, auth_headers):
    """GET /api/orders with page_size=51 → 422 (le=50 validation)."""
    headers = await auth_headers(code="order_psize51_test")
    resp = await client.get("/api/orders", headers=headers, params={
        "page_size": 51,
    })
    assert resp.status_code == 422


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

"""
Tests for order endpoints: create, list, pay, empty-cart rejection.
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


# ── Order tests ───────────────────────────────────────────────────────

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


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

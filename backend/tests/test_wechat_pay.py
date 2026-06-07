"""
Tests for WeChat Pay integration endpoints.
All tests run in dev mode (RUN_MODE=dev) which uses mock payment.
"""

import pytest


# ── Helpers ───────────────────────────────────────────────────────────

async def _create_address(client, headers, suffix=""):
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


async def _add_to_cart(client, headers, product_id=1, quantity=1):
    resp = await client.post("/api/cart/items", json={
        "product_id": product_id, "quantity": quantity,
    }, headers=headers)
    assert resp.status_code == 200


async def _create_order(client, headers, address_id):
    """Create an order and return it."""
    cart = await client.get("/api/cart", headers=headers)
    item_ids = [item["id"] for item in cart.json()["items"]]

    resp = await client.post("/api/orders", json={
        "address_id": address_id,
        "item_ids": item_ids,
        "payment_method": "wechat",
    }, headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ── /api/orders/{id}/pay tests ────────────────────────────────────────

async def test_pay_order_dev_mode(client, auth_headers):
    """POST /api/orders/{id}/pay should work in dev mode (mock payment)."""
    headers = await auth_headers(code="pay_dev_test")
    addr_id = await _create_address(client, headers, "PayDev")
    await _add_to_cart(client, headers)
    order = await _create_order(client, headers, addr_id)

    assert order["status"] == "pending"

    resp = await client.post(f"/api/orders/{order['id']}/pay", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "successful" in data["message"].lower() or "ok" in data.get("message", "").lower()

    # Verify order status changed to paid
    detail = await client.get(f"/api/orders/{order['id']}", headers=headers)
    assert detail.json()["status"] == "paid"


async def test_pay_order_already_paid(client, auth_headers):
    """Paying an already paid order → 400."""
    headers = await auth_headers(code="pay_twice_test")
    addr_id = await _create_address(client, headers, "PayTwice")
    await _add_to_cart(client, headers)
    order = await _create_order(client, headers, addr_id)

    # First payment
    await client.post(f"/api/orders/{order['id']}/pay", headers=headers)
    # Second payment attempt
    resp = await client.post(f"/api/orders/{order['id']}/pay", headers=headers)
    assert resp.status_code == 400


async def test_pay_other_user_order(client, auth_headers):
    """User A cannot pay User B's order."""
    headers_a = await auth_headers(code="user_a")
    addr_a = await _create_address(client, headers_a, "A")
    await _add_to_cart(client, headers_a)
    order = await _create_order(client, headers_a, addr_a)

    headers_b = await auth_headers(code="user_b")
    resp = await client.post(f"/api/orders/{order['id']}/pay", headers=headers_b)
    assert resp.status_code == 404


async def test_pay_nonexistent_order(client, auth_headers):
    """Pay non-existent order → 404."""
    headers = await auth_headers(code="pay_404_test")
    resp = await client.post("/api/orders/99999/pay", headers=headers)
    assert resp.status_code == 404


# ── /api/orders/{id}/wechat-pay tests ─────────────────────────────────

async def test_wechat_pay_dev_mode(client, auth_headers):
    """POST /api/orders/{id}/wechat-pay should return mock prepay params in dev mode."""
    headers = await auth_headers(code="wpay_dev_test")
    addr_id = await _create_address(client, headers, "WPayDev")
    await _add_to_cart(client, headers)
    order = await _create_order(client, headers, addr_id)

    resp = await client.post(f"/api/orders/{order['id']}/wechat-pay", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Check all required fields for wx.requestPayment()
    assert "appId" in data
    assert "timeStamp" in data
    assert "nonceStr" in data
    assert "package" in data
    assert data["package"].startswith("prepay_id=")
    assert "signType" in data
    assert "paySign" in data

    # In dev mode, paySign should be mock
    assert data["paySign"] == "MOCK_SIGNATURE"


async def test_wechat_pay_already_paid(client, auth_headers):
    """WeChat Pay on already paid order → 400."""
    headers = await auth_headers(code="wpay_paid_test")
    addr_id = await _create_address(client, headers, "WPayPaid")
    await _add_to_cart(client, headers)
    order = await _create_order(client, headers, addr_id)

    # Pay first via mock
    await client.post(f"/api/orders/{order['id']}/pay", headers=headers)
    # Try wechat-pay now
    resp = await client.post(f"/api/orders/{order['id']}/wechat-pay", headers=headers)
    assert resp.status_code == 400


async def test_wechat_pay_nonexistent_order(client, auth_headers):
    """WeChat Pay non-existent order → 404."""
    headers = await auth_headers(code="wpay_404_test")
    resp = await client.post("/api/orders/99999/wechat-pay", headers=headers)
    assert resp.status_code == 404


# ── /api/wechat-pay/notify tests ──────────────────────────────────────

async def test_notify_dev_mode(client, auth_headers):
    """POST /api/wechat-pay/notify should work in dev mode (mock)."""
    headers = await auth_headers(code="notify_test")
    addr_id = await _create_address(client, headers, "Notify")
    await _add_to_cart(client, headers)
    order = await _create_order(client, headers, addr_id)

    # Simulate a payment notification (dev mode bypasses signature verification)
    notify_body = {
        "id": "mock-notify-id",
        "create_time": "2026-06-07T12:00:00+08:00",
        "resource_type": "encrypt-resource",
        "event_type": "TRANSACTION.SUCCESS",
        "resource": {
            "algorithm": "AEAD_AES_256_GCM",
            "ciphertext": "mock_cipher",
            "nonce": "mock_nonce",
            "associated_data": "mock_ad",
        }
    }
    resp = await client.post(
        "/api/wechat-pay/notify",
        json=notify_body,
        headers={
            "wechatpay-timestamp": "1717766400",
            "wechatpay-nonce": "test_nonce_123",
            "wechatpay-signature": "test_signature",
            "wechatpay-serial": "test_serial",
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "SUCCESS"


async def test_notify_missing_signature_headers(client):
    """Notify without signature headers should still work in dev mode (mock verification)."""
    resp = await client.post("/api/wechat-pay/notify", json={
        "id": "test",
        "resource": {
            "ciphertext": "test",
            "nonce": "test",
            "associated_data": "test",
        }
    })
    assert resp.status_code == 200
    assert resp.json()["code"] == "SUCCESS"


# ── wechat_pay module unit tests ──────────────────────────────────────

async def test_yuan_to_fen():
    """Test yuan-to-fen conversion."""
    from app.wechat_pay import yuan_to_fen
    assert yuan_to_fen(0.01) == 1
    assert yuan_to_fen(1.00) == 100
    assert yuan_to_fen(49.99) == 4999
    assert yuan_to_fen(100.00) == 10000


async def test_generate_nonce_str():
    """Test nonce string generation."""
    from app.wechat_pay import generate_nonce_str
    n1 = generate_nonce_str()
    n2 = generate_nonce_str(32)
    assert len(n1) == 32
    assert len(n2) == 32
    assert n1 != n2  # Should be random


async def test_build_prepay_response():
    """Test mock prepay response structure."""
    from app.wechat_pay import _build_prepay_response
    result = _build_prepay_response("prepay_test_123")
    assert result["package"] == "prepay_id=prepay_test_123"
    assert result["signType"] == "RSA"
    assert len(result["nonceStr"]) == 32


async def test_verify_notify_signature_dev():
    """Dev mode should always return True for signature verification."""
    from app.wechat_pay import verify_notify_signature
    result = verify_notify_signature("123", "abc", "sig", "body")
    assert result is True

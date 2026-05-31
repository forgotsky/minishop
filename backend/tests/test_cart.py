"""
Tests for shopping-cart endpoints: add, list, update quantity, remove.
"""

import pytest


# ── Cart CRUD ─────────────────────────────────────────────────────────

async def test_add_to_cart(client, auth_headers):
    """POST /api/cart/items adds a product to the user's cart."""
    headers = await auth_headers(code="cart_add_test")
    resp = await client.post("/api/cart/items", json={
        "product_id": 1,
        "quantity": 2,
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Added to cart"

    # Verify the item actually appears in the cart
    cart = await client.get("/api/cart", headers=headers)
    assert cart.status_code == 200
    items = cart.json()["items"]
    assert len(items) == 1
    assert items[0]["product_id"] == 1
    assert items[0]["quantity"] == 2


async def test_get_cart_empty(client, auth_headers):
    """GET /api/cart for a new user returns an empty cart."""
    headers = await auth_headers(code="cart_empty_test")
    resp = await client.get("/api/cart", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_update_cart_quantity(client, auth_headers):
    """PUT /api/cart/items/{id}?quantity=N updates the item quantity."""
    headers = await auth_headers(code="cart_update_test")

    # Add item
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)

    # Get cart to discover the item id
    cart = await client.get("/api/cart", headers=headers)
    item_id = cart.json()["items"][0]["id"]

    # Update quantity to 5
    resp = await client.put(
        f"/api/cart/items/{item_id}",
        params={"quantity": 5},
        headers=headers,
    )
    assert resp.status_code == 200

    # Verify the change
    cart2 = await client.get("/api/cart", headers=headers)
    assert cart2.json()["items"][0]["quantity"] == 5
    # subtotal = price * quantity = 49.99 * 5
    # Use approx because 49.99*5 yields 249.95000000000002 in floating point
    assert cart2.json()["items"][0]["subtotal"] == pytest.approx(249.95, rel=0.01)


async def test_remove_from_cart(client, auth_headers):
    """DELETE /api/cart/items/{id} removes the item; cart becomes empty."""
    headers = await auth_headers(code="cart_remove_test")

    # Add item
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)

    # Get cart to discover the item id
    cart = await client.get("/api/cart", headers=headers)
    item_id = cart.json()["items"][0]["id"]

    # Remove item
    resp = await client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert resp.status_code == 200

    # Cart should be empty now
    cart2 = await client.get("/api/cart", headers=headers)
    assert cart2.json()["items"] == []
    assert cart2.json()["total"] == 0


# ── Negative tests ────────────────────────────────────────────────────

async def test_add_to_cart_product_404(client, auth_headers):
    """POST /api/cart/items with a non-existent product_id → 404."""
    headers = await auth_headers(code="cart_404_test")
    resp = await client.post("/api/cart/items", json={
        "product_id": 9999,
        "quantity": 1,
    }, headers=headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_add_to_cart_out_of_stock(client, auth_headers):
    """POST /api/cart/items with quantity > stock → 400."""
    headers = await auth_headers(code="cart_oos_test")
    # Product 1 has stock=120, request 9999
    resp = await client.post("/api/cart/items", json={
        "product_id": 1,
        "quantity": 9999,
    }, headers=headers)
    assert resp.status_code == 400
    assert "stock" in resp.json()["detail"].lower()


async def test_update_cart_item_404(client, auth_headers):
    """PUT /api/cart/items/9999 (non-existent) → 404."""
    headers = await auth_headers(code="cart_upd404_test")
    resp = await client.put("/api/cart/items/9999", params={"quantity": 3}, headers=headers)
    assert resp.status_code == 404


async def test_remove_cart_item_404(client, auth_headers):
    """DELETE /api/cart/items/9999 (non-existent) → 404."""
    headers = await auth_headers(code="cart_del404_test")
    resp = await client.delete("/api/cart/items/9999", headers=headers)
    assert resp.status_code == 404


# ── Cross-user isolation ──────────────────────────────────────────────

async def test_cart_cross_user_isolation(client, auth_headers):
    """User B cannot access User A's cart items."""
    headers_a = await auth_headers(code="cart_user_a")
    headers_b = await auth_headers(code="cart_user_b")

    # User A adds item to cart
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers_a)

    # Get User A's cart to discover the item id
    cart_a = await client.get("/api/cart", headers=headers_a)
    assert len(cart_a.json()["items"]) == 1
    item_id = cart_a.json()["items"][0]["id"]

    # User B's cart is empty (does not see User A's items)
    cart_b = await client.get("/api/cart", headers=headers_b)
    assert cart_b.json()["items"] == []

    # User B cannot update User A's cart item → 404
    resp = await client.put(f"/api/cart/items/{item_id}", params={"quantity": 5}, headers=headers_b)
    assert resp.status_code == 404


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

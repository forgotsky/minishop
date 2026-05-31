"""
Tests for shopping-cart endpoints: add, list, update quantity, remove, clear,
cross-user isolation, and edge cases.
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
    # The code rounds subtotals to 2 decimal places (main.py line 414),
    # so the result is exactly 249.95
    assert cart2.json()["items"][0]["subtotal"] == 249.95


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


async def test_clear_cart(client, auth_headers):
    """DELETE /api/cart removes all items from the user's cart."""
    headers = await auth_headers(code="cart_clear_test")

    # Add multiple items
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 2,
    }, headers=headers)
    await client.post("/api/cart/items", json={
        "product_id": 2, "quantity": 1,
    }, headers=headers)

    # Verify cart has items
    cart_before = await client.get("/api/cart", headers=headers)
    assert len(cart_before.json()["items"]) == 2

    # Clear cart
    resp = await client.delete("/api/cart", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Cart cleared"

    # Verify cart is empty
    cart_after = await client.get("/api/cart", headers=headers)
    assert cart_after.json()["items"] == []
    assert cart_after.json()["total"] == 0


async def test_add_same_product_increments_quantity(client, auth_headers):
    """Adding the same product twice merges into one cart item with summed quantity."""
    headers = await auth_headers(code="cart_same_product_test")

    # Add product 1 with quantity 2
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 2,
    }, headers=headers)

    # Add the same product again with quantity 3
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 3,
    }, headers=headers)

    # Cart should have only 1 line item with quantity 5
    cart = await client.get("/api/cart", headers=headers)
    items = cart.json()["items"]
    assert len(items) == 1
    assert items[0]["product_id"] == 1
    assert items[0]["quantity"] == 5


async def test_cart_with_multiple_products(client, auth_headers):
    """Cart total is correctly calculated with multiple different products."""
    headers = await auth_headers(code="cart_multi_test")

    # Product 1: 49.99 * 2 = 99.98
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 2,
    }, headers=headers)

    # Product 2: 89.00 * 1 = 89.00
    await client.post("/api/cart/items", json={
        "product_id": 2, "quantity": 1,
    }, headers=headers)

    cart = await client.get("/api/cart", headers=headers)
    data = cart.json()
    assert len(data["items"]) == 2
    # total = 99.98 + 89.00 = 188.98
    assert data["total"] == 188.98


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


async def test_add_to_cart_product_not_on_sale(client, auth_headers):
    """POST /api/cart/items with a product that is not on sale → 404."""
    from app.db import SessionLocal
    from app.models import Product

    headers = await auth_headers(code="cart_offsale_test")
    # Set product 8 (Desk Lamp) to is_on_sale=False via direct DB access
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == 8).first()
        assert product is not None, "Product 8 (Desk Lamp) must exist in seed data"
        product.is_on_sale = False
        db.commit()
    finally:
        db.close()
    # Now attempt to add this off-sale product to cart → 404
    resp = await client.post("/api/cart/items", json={
        "product_id": 8,
        "quantity": 1,
    }, headers=headers)
    assert resp.status_code == 404


async def test_add_to_cart_zero_quantity(client, auth_headers):
    """POST /api/cart/items with quantity=0 → 422 validation error."""
    headers = await auth_headers(code="cart_zeroq_test")
    resp = await client.post("/api/cart/items", json={
        "product_id": 1,
        "quantity": 0,
    }, headers=headers)
    assert resp.status_code == 422


async def test_add_to_cart_negative_quantity(client, auth_headers):
    """POST /api/cart/items with negative quantity → 422 validation error."""
    headers = await auth_headers(code="cart_negq_test")
    resp = await client.post("/api/cart/items", json={
        "product_id": 1,
        "quantity": -1,
    }, headers=headers)
    assert resp.status_code == 422


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


async def test_cart_requires_auth(client):
    """All cart endpoints require authentication → 401 or 403 without token."""
    # GET /api/cart
    resp = await client.get("/api/cart")
    assert resp.status_code == 401

    # POST /api/cart/items
    resp = await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    })
    assert resp.status_code == 401

    # PUT /api/cart/items/1
    resp = await client.put("/api/cart/items/1", params={"quantity": 2})
    assert resp.status_code == 401

    # DELETE /api/cart/items/1
    resp = await client.delete("/api/cart/items/1")
    assert resp.status_code == 401

    # DELETE /api/cart (clear)
    resp = await client.delete("/api/cart")
    assert resp.status_code == 401


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


async def test_cart_cross_user_clear_isolation(client, auth_headers):
    """User B clearing their cart does not affect User A's cart."""
    headers_a = await auth_headers(code="cart_clear_iso_a")
    headers_b = await auth_headers(code="cart_clear_iso_b")

    # User A adds items
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 2,
    }, headers=headers_a)

    # User B adds items
    await client.post("/api/cart/items", json={
        "product_id": 2, "quantity": 1,
    }, headers=headers_b)

    # User B clears their cart
    resp = await client.delete("/api/cart", headers=headers_b)
    assert resp.status_code == 200

    # User A's cart should still have items
    cart_a = await client.get("/api/cart", headers=headers_a)
    assert len(cart_a.json()["items"]) == 1
    assert cart_a.json()["items"][0]["product_id"] == 1

    # User B's cart should be empty
    cart_b = await client.get("/api/cart", headers=headers_b)
    assert cart_b.json()["items"] == []


async def test_cart_cross_user_delete_isolation(client, auth_headers):
    """User B cannot delete User A's specific cart item."""
    headers_a = await auth_headers(code="cart_del_iso_a")
    headers_b = await auth_headers(code="cart_del_iso_b")

    # User A adds item
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers_a)
    cart_a = await client.get("/api/cart", headers=headers_a)
    item_id = cart_a.json()["items"][0]["id"]

    # User B tries to delete User A's item → 404
    resp = await client.delete(f"/api/cart/items/{item_id}", headers=headers_b)
    assert resp.status_code == 404

    # User A's item is still there
    cart_a2 = await client.get("/api/cart", headers=headers_a)
    assert len(cart_a2.json()["items"]) == 1


# ── PUT quantity validation edge cases ────────────────────────────────

async def test_update_cart_quantity_zero(client, auth_headers):
    """PUT /api/cart/items/{id}?quantity=0 → 422 (below minimum 1)."""
    headers = await auth_headers(code="cart_upd_qty0_test")

    # Add item to cart
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    cart = await client.get("/api/cart", headers=headers)
    item_id = cart.json()["items"][0]["id"]

    resp = await client.put(
        f"/api/cart/items/{item_id}",
        params={"quantity": 0},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_update_cart_quantity_exceed_max(client, auth_headers):
    """PUT /api/cart/items/{id}?quantity=100 → 422 (above maximum 99)."""
    headers = await auth_headers(code="cart_upd_qty100_test")

    # Add item to cart
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    cart = await client.get("/api/cart", headers=headers)
    item_id = cart.json()["items"][0]["id"]

    resp = await client.put(
        f"/api/cart/items/{item_id}",
        params={"quantity": 100},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_update_cart_quantity_missing(client, auth_headers):
    """PUT /api/cart/items/{id} without quantity parameter → 422."""
    headers = await auth_headers(code="cart_upd_noparam_test")

    # Add item to cart
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)
    cart = await client.get("/api/cart", headers=headers)
    item_id = cart.json()["items"][0]["id"]

    resp = await client.put(
        f"/api/cart/items/{item_id}",
        headers=headers,
    )
    assert resp.status_code == 422


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

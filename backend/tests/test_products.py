"""
Tests for product-related endpoints: list, detail, filtering, search.
"""

import pytest


# ── Product list / detail ─────────────────────────────────────────────

async def test_list_products(client):
    """GET /api/products returns seeded products (all on_sale)."""
    resp = await client.get("/api/products")
    assert resp.status_code == 200
    data = resp.json()
    assert "products" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["products"]) >= 1
    # Each product should have required fields
    for p in data["products"]:
        assert "id" in p
        assert "name" in p
        assert "price" in p
        assert "category" in p
        assert "stock" in p


async def test_get_product_by_id(client):
    """GET /api/products/1 returns the first seeded product."""
    resp = await client.get("/api/products/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Wireless Headphones"
    assert data["price"] == 49.99
    assert data["category"] == "electronics"


async def test_get_product_404(client):
    """GET /api/products/999 returns 404 for non-existent product."""
    resp = await client.get("/api/products/999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── Filtering / search ────────────────────────────────────────────────

async def test_filter_by_category(client):
    """GET /api/products?category=electronics returns only electronics (4 products)."""
    resp = await client.get("/api/products", params={"category": "electronics"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    for p in data["products"]:
        assert p["category"] == "electronics"


async def test_search_products(client):
    """GET /api/products?search=watch returns 1 result: Smart Watch."""
    resp = await client.get("/api/products", params={"search": "watch"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert "Watch" in data["products"][0]["name"]


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

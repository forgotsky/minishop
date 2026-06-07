"""
Tests for product-related endpoints: list, detail, pagination, filtering, search, categories.
"""

import pytest


# ── Product list ──────────────────────────────────────────────────────

async def test_list_products(client):
    """GET /api/products returns seeded products (all on_sale)."""
    resp = await client.get("/api/products")
    assert resp.status_code == 200
    data = resp.json()
    assert "products" in data
    assert "total" in data
    assert data["total"] == 8
    assert len(data["products"]) == 8
    # Each product should have required fields
    for p in data["products"]:
        assert "id" in p
        assert "name" in p
        assert "price" in p
        assert "category" in p
        assert "stock" in p


# ── Product detail ────────────────────────────────────────────────────

async def test_get_product_by_id(client):
    """GET /api/products/1 returns the first seeded product."""
    resp = await client.get("/api/products/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Wireless Headphones"
    assert data["price"] == 49.99
    assert data["category"] == "Electronics"


async def test_get_product_404(client):
    """GET /api/products/999 returns 404 for non-existent product."""
    resp = await client.get("/api/products/999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── Pagination ────────────────────────────────────────────────────────

async def test_pagination_default(client):
    """Default page=1, page_size=10 → returns all 8 products on one page."""
    resp = await client.get("/api/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["products"]) == 8


async def test_pagination_page_2_empty(client):
    """page=2 with default page_size=10 → empty list (only 8 products total)."""
    resp = await client.get("/api/products", params={"page": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["products"]) == 0


async def test_pagination_small_page_size(client):
    """page_size=3 → 3 products per page, 3 pages total."""
    # Page 1
    resp1 = await client.get("/api/products", params={"page": 1, "page_size": 3})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total"] == 8
    assert len(data1["products"]) == 3

    # Page 2
    resp2 = await client.get("/api/products", params={"page": 2, "page_size": 3})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["total"] == 8
    assert len(data2["products"]) == 3

    # Page 3 → remaining 2
    resp3 = await client.get("/api/products", params={"page": 3, "page_size": 3})
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["total"] == 8
    assert len(data3["products"]) == 2

    # Page 4 → empty
    resp4 = await client.get("/api/products", params={"page": 4, "page_size": 3})
    assert resp4.status_code == 200
    data4 = resp4.json()
    assert data4["total"] == 8
    assert len(data4["products"]) == 0


async def test_pagination_page_size_one(client):
    """page_size=1 → 1 product per page, verify no duplicates across pages."""
    seen_ids = set()
    for page in range(1, 10):
        resp = await client.get("/api/products", params={"page": page, "page_size": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 8
        if page <= 8:
            assert len(data["products"]) == 1
            pid = data["products"][0]["id"]
            assert pid not in seen_ids, f"Product {pid} duplicated on page {page}"
            seen_ids.add(pid)
        else:
            assert len(data["products"]) == 0

    assert len(seen_ids) == 8


async def test_pagination_max_page_size(client):
    """page_size=50 (max allowed) → all 8 products on one page."""
    resp = await client.get("/api/products", params={"page_size": 50})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8
    assert len(data["products"]) == 8


async def test_pagination_page_zero(client):
    """page=0 → FastAPI Query(ge=1) validation → 422."""
    resp = await client.get("/api/products", params={"page": 0})
    assert resp.status_code == 422


async def test_pagination_negative_page(client):
    """page=-1 → FastAPI Query(ge=1) validation → 422."""
    resp = await client.get("/api/products", params={"page": -1})
    assert resp.status_code == 422


async def test_pagination_page_size_zero(client):
    """page_size=0 → FastAPI Query(ge=1) validation → 422."""
    resp = await client.get("/api/products", params={"page_size": 0})
    assert resp.status_code == 422


async def test_pagination_page_size_exceeds_max(client):
    """page_size=51 → FastAPI Query(le=50) validation → 422."""
    resp = await client.get("/api/products", params={"page_size": 51})
    assert resp.status_code == 422


# ── Category filter ───────────────────────────────────────────────────

async def test_filter_by_category_electronics(client):
    """GET /api/products?category=electronics returns 4 electronics products."""
    resp = await client.get("/api/products", params={"category": "electronics"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    for p in data["products"]:
        assert p["category"] == "Electronics"


async def test_filter_by_category_sports(client):
    """GET /api/products?category=sports returns 1 product."""
    resp = await client.get("/api/products", params={"category": "sports"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["products"][0]["name"] == "Running Shoes"


async def test_filter_by_category_accessories(client):
    """GET /api/products?category=accessories returns 1 product."""
    resp = await client.get("/api/products", params={"category": "accessories"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["products"][0]["name"] == "Backpack"


async def test_filter_by_category_kitchen(client):
    """GET /api/products?category=kitchen returns 1 product."""
    resp = await client.get("/api/products", params={"category": "kitchen"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["products"][0]["name"] == "Coffee Mug"


async def test_filter_by_category_home(client):
    """GET /api/products?category=home returns 1 product."""
    resp = await client.get("/api/products", params={"category": "home"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["products"][0]["name"] == "Desk Lamp"


async def test_filter_by_nonexistent_category(client):
    """GET /api/products?category=nonexistent returns 0 products."""
    resp = await client.get("/api/products", params={"category": "nonexistent"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert len(data["products"]) == 0


async def test_filter_by_empty_category(client):
    """GET /api/products?category= (empty) is treated as no filter → all products."""
    resp = await client.get("/api/products", params={"category": ""})
    assert resp.status_code == 200
    data = resp.json()
    # Empty string is falsy in Python, so the filter is skipped → all 8
    assert data["total"] == 8


async def test_filter_category_with_pagination(client):
    """Category filter combined with pagination: electronics, page_size=2."""
    resp = await client.get("/api/products", params={
        "category": "electronics",
        "page_size": 2,
        "page": 2,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4  # 4 electronics total
    assert len(data["products"]) == 2  # page 2 of 2-per-page = 2 items
    for p in data["products"]:
        assert p["category"] == "Electronics"


# ── Search ──────────────────────────────────────────────────────────

async def test_search_products_exact(client):
    """GET /api/products?search=watch returns 1 result: Smart Watch."""
    resp = await client.get("/api/products", params={"search": "watch"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert "Watch" in data["products"][0]["name"]


async def test_search_case_insensitive(client):
    """Search is case-insensitive: 'WATCH' and 'watch' should return same results."""
    resp_lower = await client.get("/api/products", params={"search": "watch"})
    resp_upper = await client.get("/api/products", params={"search": "WATCH"})
    resp_mixed = await client.get("/api/products", params={"search": "WaTcH"})

    assert resp_lower.status_code == 200
    assert resp_upper.status_code == 200
    assert resp_mixed.status_code == 200

    assert resp_lower.json()["total"] == resp_upper.json()["total"]
    assert resp_upper.json()["total"] == resp_mixed.json()["total"]


async def test_search_partial_match(client):
    """Search 'bank' matches 'Power Bank'."""
    resp = await client.get("/api/products", params={"search": "bank"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["products"][0]["name"] == "Power Bank"


async def test_search_single_match_wireless(client):
    """Search 'wireless' matches only 'Wireless Headphones' (search matches name, not description)."""
    resp = await client.get("/api/products", params={"search": "wireless"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["products"][0]["name"] == "Wireless Headphones"


async def test_search_no_results(client):
    """Search 'xyz_not_found' returns 0 products."""
    resp = await client.get("/api/products", params={"search": "xyz_not_found"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert len(data["products"]) == 0


async def test_search_single_character(client):
    """Search with a single character 'a' matches multiple products."""
    resp = await client.get("/api/products", params={"search": "a"})
    assert resp.status_code == 200
    data = resp.json()
    # "a" appears in: Smart Watch, Backpack, Desk Lamp, Power Bank
    assert data["total"] >= 3


async def test_search_empty_string(client):
    """Search with empty string treated as no filter → all products."""
    resp = await client.get("/api/products", params={"search": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 8


async def test_search_combined_with_category(client):
    """Combined search + category: category=electronics, search=bank → only Power Bank."""
    resp = await client.get("/api/products", params={
        "category": "electronics",
        "search": "bank",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["products"][0]["name"] == "Power Bank"


async def test_search_combined_with_category_no_match(client):
    """Combined search + category where no product matches both → 0 results."""
    resp = await client.get("/api/products", params={
        "category": "sports",
        "search": "wireless",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


# ── Categories endpoint ──────────────────────────────────────────────

async def test_list_categories(client):
    """GET /api/categories returns distinct categories from on_sale products."""
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    expected = {"Electronics", "Accessories", "Sports", "Kitchen", "Home"}
    assert set(data["categories"]) == expected


# ── Ordering: products sorted by sales_count desc ─────────────────────

async def test_products_sorted_by_sales_count_desc(client):
    """Products are returned in descending order of sales_count."""
    resp = await client.get("/api/products")
    assert resp.status_code == 200
    products = resp.json()["products"]
    sales = [p["sales_count"] for p in products]
    assert sales == sorted(sales, reverse=True), f"Not sorted desc: {sales}"


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

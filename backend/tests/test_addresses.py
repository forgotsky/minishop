"""
Tests for address CRUD endpoints: create, list, update, delete,
validation, default-flag behavior, cross-user isolation, and edge cases.
"""

import pytest


# ── Address CRUD ─────────────────────────────────────────────────────

async def test_create_address(client, auth_headers):
    """POST /api/addresses creates a new address and returns it."""
    headers = await auth_headers(code="addr_create_test")
    resp = await client.post("/api/addresses", json={
        "full_name": "Test User",
        "phone": "13800138000",
        "province": "Guangdong",
        "city": "Shenzhen",
        "district": "Nanshan",
        "street": "123 Tech Road",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] > 0
    assert data["full_name"] == "Test User"
    assert data["phone"] == "13800138000"
    assert data["province"] == "Guangdong"
    assert data["city"] == "Shenzhen"
    assert data["district"] == "Nanshan"
    assert data["street"] == "123 Tech Road"
    assert data["is_default"] is False


async def test_list_addresses(client, auth_headers):
    """GET /api/addresses returns a list of the user's addresses."""
    headers = await auth_headers(code="addr_list_test")
    # Create a couple of addresses
    await client.post("/api/addresses", json={
        "full_name": "User One", "phone": "11111111111",
        "province": "A", "city": "B", "district": "C", "street": "D1",
    }, headers=headers)
    await client.post("/api/addresses", json={
        "full_name": "User Two", "phone": "22222222222",
        "province": "A", "city": "B", "district": "C", "street": "D2",
    }, headers=headers)

    resp = await client.get("/api/addresses", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["full_name"] == "User One"
    assert data[1]["full_name"] == "User Two"


async def test_list_addresses_empty(client, auth_headers):
    """GET /api/addresses for a new user returns an empty list."""
    headers = await auth_headers(code="addr_empty_test")
    resp = await client.get("/api/addresses", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_update_address(client, auth_headers):
    """PUT /api/addresses/{id} updates an existing address."""
    headers = await auth_headers(code="addr_update_test")
    # Create an address
    create_resp = await client.post("/api/addresses", json={
        "full_name": "Old Name", "phone": "13800138000",
        "province": "Old", "city": "Old", "district": "Old", "street": "Old",
    }, headers=headers)
    addr_id = create_resp.json()["id"]

    # Update it
    resp = await client.put(f"/api/addresses/{addr_id}", json={
        "full_name": "New Name", "phone": "13900139000",
        "province": "New", "city": "New", "district": "New", "street": "New",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == addr_id
    assert data["full_name"] == "New Name"
    assert data["phone"] == "13900139000"
    assert data["province"] == "New"

    # Verify via list
    list_resp = await client.get("/api/addresses", headers=headers)
    updated = list_resp.json()[0]
    assert updated["full_name"] == "New Name"


async def test_delete_address(client, auth_headers):
    """DELETE /api/addresses/{id} removes the address."""
    headers = await auth_headers(code="addr_delete_test")
    # Create an address
    create_resp = await client.post("/api/addresses", json={
        "full_name": "To Delete", "phone": "13800138000",
        "province": "A", "city": "B", "district": "C", "street": "D",
    }, headers=headers)
    addr_id = create_resp.json()["id"]

    # Delete it
    resp = await client.delete(f"/api/addresses/{addr_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Address deleted"

    # Verify gone
    list_resp = await client.get("/api/addresses", headers=headers)
    assert list_resp.json() == []


# ── Validation ───────────────────────────────────────────────────────

async def test_create_address_short_name(client, auth_headers):
    """POST /api/addresses with full_name < 2 chars → 422 validation error."""
    headers = await auth_headers(code="addr_short_name")
    resp = await client.post("/api/addresses", json={
        "full_name": "A",  # min_length=2
        "phone": "13800138000",
        "province": "A", "city": "B", "district": "C", "street": "D",
    }, headers=headers)
    assert resp.status_code == 422


async def test_create_address_short_phone(client, auth_headers):
    """POST /api/addresses with phone < 5 chars → 422 validation error."""
    headers = await auth_headers(code="addr_short_phone")
    resp = await client.post("/api/addresses", json={
        "full_name": "Test User",
        "phone": "1234",  # min_length=5
        "province": "A", "city": "B", "district": "C", "street": "D",
    }, headers=headers)
    assert resp.status_code == 422


async def test_create_address_missing_required_field(client, auth_headers):
    """POST /api/addresses without required field 'city' → 422."""
    headers = await auth_headers(code="addr_missing_field")
    resp = await client.post("/api/addresses", json={
        "full_name": "Test User",
        "phone": "13800138000",
        "province": "A",
        # city missing
        "district": "C",
        "street": "D",
    }, headers=headers)
    assert resp.status_code == 422


# ── Default flag behavior ────────────────────────────────────────────

async def test_address_default_flag_sets_default(client, auth_headers):
    """Creating an address with is_default=True makes it the default."""
    headers = await auth_headers(code="addr_def_set")
    resp = await client.post("/api/addresses", json={
        "full_name": "Default User", "phone": "13800138000",
        "province": "A", "city": "B", "district": "C", "street": "D",
        "is_default": True,
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True


async def test_address_default_flag_replaces_previous(client, auth_headers):
    """Setting is_default=True on a new address unsets the previous default."""
    headers = await auth_headers(code="addr_def_replace")
    # Create first address as default
    await client.post("/api/addresses", json={
        "full_name": "First Default", "phone": "11111111111",
        "province": "A", "city": "B", "district": "C", "street": "D1",
        "is_default": True,
    }, headers=headers)

    # Create second address as default (should unset the first)
    resp = await client.post("/api/addresses", json={
        "full_name": "Second Default", "phone": "22222222222",
        "province": "A", "city": "B", "district": "C", "street": "D2",
        "is_default": True,
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True

    # First address should no longer be default
    addrs = await client.get("/api/addresses", headers=headers)
    first = [a for a in addrs.json() if a["full_name"] == "First Default"][0]
    assert first["is_default"] is False


# ── Cross-user isolation (IDOR) ──────────────────────────────────────

async def test_address_cross_user_list_isolation(client, auth_headers):
    """User B cannot see User A's addresses in their list."""
    headers_a = await auth_headers(code="addr_list_iso_a")
    headers_b = await auth_headers(code="addr_list_iso_b")

    # User A creates two addresses
    await client.post("/api/addresses", json={
        "full_name": "AddrA1", "phone": "11111111111",
        "province": "A", "city": "B", "district": "C", "street": "D1",
    }, headers=headers_a)
    await client.post("/api/addresses", json={
        "full_name": "AddrA2", "phone": "22222222222",
        "province": "A", "city": "B", "district": "C", "street": "D2",
    }, headers=headers_a)

    # User B's list is empty (does not see User A's addresses)
    list_b = await client.get("/api/addresses", headers=headers_b)
    assert list_b.status_code == 200
    assert list_b.json() == []

    # User A's list has both addresses
    list_a = await client.get("/api/addresses", headers=headers_a)
    assert len(list_a.json()) == 2


async def test_address_cross_user_update(client, auth_headers):
    """User B cannot update User A's address → 404 (IDOR protection)."""
    headers_a = await auth_headers(code="addr_upd_iso_a")
    headers_b = await auth_headers(code="addr_upd_iso_b")

    # User A creates an address
    create_resp = await client.post("/api/addresses", json={
        "full_name": "AddrA", "phone": "13800138000",
        "province": "A", "city": "B", "district": "C", "street": "D",
    }, headers=headers_a)
    addr_id = create_resp.json()["id"]

    # User B tries to update User A's address → 404
    resp = await client.put(f"/api/addresses/{addr_id}", json={
        "full_name": "Hacked", "phone": "99999999999",
        "province": "X", "city": "Y", "district": "Z", "street": "X",
    }, headers=headers_b)
    assert resp.status_code == 404

    # User A's address is unchanged
    list_a = await client.get("/api/addresses", headers=headers_a)
    assert list_a.json()[0]["full_name"] == "AddrA"


async def test_address_cross_user_delete(client, auth_headers):
    """User B cannot delete User A's address → 404 (IDOR protection)."""
    headers_a = await auth_headers(code="addr_del_iso_a")
    headers_b = await auth_headers(code="addr_del_iso_b")

    # User A creates an address
    create_resp = await client.post("/api/addresses", json={
        "full_name": "AddrA", "phone": "13800138000",
        "province": "A", "city": "B", "district": "C", "street": "D",
    }, headers=headers_a)
    addr_id = create_resp.json()["id"]

    # User B tries to delete User A's address → 404
    resp = await client.delete(f"/api/addresses/{addr_id}", headers=headers_b)
    assert resp.status_code == 404

    # User A's address still exists
    list_a = await client.get("/api/addresses", headers=headers_a)
    assert len(list_a.json()) == 1


# ── 404 on non-existent resources ────────────────────────────────────

async def test_update_nonexistent_address(client, auth_headers):
    """PUT /api/addresses/9999 (non-existent id) → 404."""
    headers = await auth_headers(code="addr_upd_404")
    resp = await client.put("/api/addresses/9999", json={
        "full_name": "Ghost", "phone": "13800138000",
        "province": "A", "city": "B", "district": "C", "street": "D",
    }, headers=headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_delete_nonexistent_address(client, auth_headers):
    """DELETE /api/addresses/9999 (non-existent id) → 404."""
    headers = await auth_headers(code="addr_del_404")
    resp = await client.delete("/api/addresses/9999", headers=headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── Auth required ────────────────────────────────────────────────────

async def test_address_requires_auth(client):
    """All address endpoints require authentication → 401 without token."""
    # GET /api/addresses
    resp = await client.get("/api/addresses")
    assert resp.status_code == 401

    # POST /api/addresses
    resp = await client.post("/api/addresses", json={
        "full_name": "Test", "phone": "13800138000",
        "province": "A", "city": "B", "district": "C", "street": "D",
    })
    assert resp.status_code == 401

    # PUT /api/addresses/1
    resp = await client.put("/api/addresses/1", json={
        "full_name": "Test", "phone": "13800138000",
        "province": "A", "city": "B", "district": "C", "street": "D",
    })
    assert resp.status_code == 401

    # DELETE /api/addresses/1
    resp = await client.delete("/api/addresses/1")
    assert resp.status_code == 401


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

"""
Tests for authentication endpoints: login, protected-endpoint guards.
"""

import pytest


# ── Login tests ────────────────────────────────────────────────────────

async def test_login_creates_user(client):
    """POST /api/auth/login with a fresh code should create a user and return a token."""
    resp = await client.post("/api/auth/login", json={
        "code": "auth_create_test",
        "nickname": "NewUser",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user_id"] > 0
    assert data["nickname"] == "NewUser"


async def test_login_existing_user(client):
    """Logging in twice with the same code returns the same user_id."""
    # First login creates the user
    resp1 = await client.post("/api/auth/login", json={"code": "auth_existing"})
    assert resp1.status_code == 200
    user_id_1 = resp1.json()["user_id"]

    # Second login with same code → same user
    resp2 = await client.post("/api/auth/login", json={"code": "auth_existing"})
    assert resp2.status_code == 200
    user_id_2 = resp2.json()["user_id"]

    assert user_id_1 == user_id_2


async def test_login_empty_code(client):
    """POST with empty code → dev mode still works (generates a timestamp-based openid)."""
    resp = await client.post("/api/auth/login", json={"code": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user_id"] > 0


# ── Protected-endpoint tests ──────────────────────────────────────────

async def test_protected_endpoint_no_token(client):
    """GET /api/cart without an Authorization header → 401."""
    resp = await client.get("/api/cart")
    assert resp.status_code == 401


async def test_protected_endpoint_with_token(client, auth_headers):
    """GET /api/cart with a valid token → 200."""
    headers = await auth_headers(code="auth_protected_test")
    resp = await client.get("/api/cart", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

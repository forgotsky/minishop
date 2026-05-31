"""
Tests for authentication endpoints: login, protected-endpoint guards, token validation.
"""

import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt


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


async def test_login_updates_nickname_on_relogin(client):
    """Re-login with a new nickname should update the stored nickname."""
    code = "auth_nick_update"
    # First login with initial nickname
    resp1 = await client.post("/api/auth/login", json={
        "code": code,
        "nickname": "OriginalNick",
    })
    assert resp1.status_code == 200
    user_id = resp1.json()["user_id"]
    assert resp1.json()["nickname"] == "OriginalNick"

    # Second login with updated nickname
    resp2 = await client.post("/api/auth/login", json={
        "code": code,
        "nickname": "UpdatedNick",
    })
    assert resp2.status_code == 200
    assert resp2.json()["user_id"] == user_id
    assert resp2.json()["nickname"] == "UpdatedNick"


async def test_login_updates_avatar_on_relogin(client):
    """Re-login with a new avatar should update the stored avatar."""
    code = "auth_avatar_update"
    resp1 = await client.post("/api/auth/login", json={
        "code": code,
        "avatar": "https://example.com/old.png",
    })
    assert resp1.status_code == 200

    resp2 = await client.post("/api/auth/login", json={
        "code": code,
        "avatar": "https://example.com/new.png",
    })
    assert resp2.status_code == 200
    # Avatar is returned via /api/user/profile (requires token)
    token = resp2.json()["token"]
    profile_resp = await client.get("/api/user/profile", headers={
        "Authorization": f"Bearer {token}",
    })
    assert profile_resp.status_code == 200
    assert profile_resp.json()["avatar"] == "https://example.com/new.png"


async def test_login_empty_code(client):
    """POST with empty code → dev mode still works (generates a timestamp-based openid)."""
    resp = await client.post("/api/auth/login", json={"code": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user_id"] > 0


async def test_login_reactivates_soft_deleted_account(client):
    """Re-login reactivates a previously soft-deleted account."""
    code = "auth_reactivate"
    # First login → create user
    resp1 = await client.post("/api/auth/login", json={"code": code})
    assert resp1.status_code == 200
    user_id = resp1.json()["user_id"]
    token = resp1.json()["token"]

    # Soft-delete the account
    del_resp = await client.delete("/api/user/account", headers={
        "Authorization": f"Bearer {token}",
    })
    assert del_resp.status_code == 200

    # Verify account is deactivated: protected endpoint should 401
    cart_resp = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {token}",
    })
    assert cart_resp.status_code == 401

    # Re-login with same code → account reactivated
    resp2 = await client.post("/api/auth/login", json={"code": code})
    assert resp2.status_code == 200
    assert resp2.json()["user_id"] == user_id

    # New token should work for protected endpoints
    new_token = resp2.json()["token"]
    cart_resp2 = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {new_token}",
    })
    assert cart_resp2.status_code == 200


async def test_login_missing_code_field(client):
    """POST /api/auth/login without a 'code' field → 422 (validation error)."""
    resp = await client.post("/api/auth/login", json={"nickname": "NoCode"})
    assert resp.status_code == 422


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


# ── Token validation tests ────────────────────────────────────────────

_SECRET = "dev-secret-change-in-production"
_ALGORITHM = "HS256"


def _forge_token(sub, exp_delta_hours=720):
    """Forge a valid JWT using the dev secret (for testing valid-token scenarios)."""
    expire = datetime.now(timezone.utc) + timedelta(hours=exp_delta_hours)
    payload = {"sub": str(sub), "exp": expire}
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


async def test_protected_endpoint_invalid_token(client):
    """GET /api/cart with a token signed with the wrong secret → 401."""
    # Forge a token with a different secret
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": "1", "exp": expire}
    bad_token = jwt.encode(payload, "wrong-secret", algorithm=_ALGORITHM)

    resp = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {bad_token}",
    })
    assert resp.status_code == 401


async def test_protected_endpoint_expired_token(client, auth_headers):
    """GET /api/cart with an expired token → 401."""
    # First get a valid token to know a real user_id
    headers = await auth_headers(code="auth_expired_test")
    token = headers["Authorization"].split(" ")[1]

    # Decode it to find the user_id, then forge an expired one
    payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    user_id = payload["sub"]

    expire = datetime.now(timezone.utc) - timedelta(hours=1)
    expired_payload = {"sub": user_id, "exp": expire}
    expired_token = jwt.encode(expired_payload, _SECRET, algorithm=_ALGORITHM)

    resp = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {expired_token}",
    })
    assert resp.status_code == 401


async def test_protected_endpoint_malformed_token(client):
    """GET /api/cart with a completely malformed token → 401."""
    resp = await client.get("/api/cart", headers={
        "Authorization": "Bearer not.a.real.jwt.token",
    })
    assert resp.status_code == 401


async def test_protected_endpoint_non_existent_user(client):
    """GET /api/cart with a valid token for a user_id that doesn't exist → 401."""
    bad_token = _forge_token(sub=999999)
    resp = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {bad_token}",
    })
    assert resp.status_code == 401


async def test_protected_endpoint_missing_sub(client):
    """GET /api/cart with a token that has no 'sub' claim → 401."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"exp": expire}  # no 'sub'
    no_sub_token = jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)

    resp = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {no_sub_token}",
    })
    assert resp.status_code == 401


async def test_protected_endpoint_non_numeric_sub(client):
    """GET /api/cart with a token whose sub is not numeric → 401."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": "not-a-number", "exp": expire}
    bad_token = jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)

    resp = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {bad_token}",
    })
    assert resp.status_code == 401


async def test_protected_endpoint_bearer_without_token(client):
    """GET /api/cart with Authorization header containing only 'Bearer ' → 401."""
    resp = await client.get("/api/cart", headers={
        "Authorization": "Bearer ",
    })
    assert resp.status_code == 401


async def test_protected_endpoint_no_bearer_prefix(client):
    """GET /api/cart with raw token (no 'Bearer ' scheme prefix) → 401."""
    token = _forge_token(sub=1)
    resp = await client.get("/api/cart", headers={
        "Authorization": token,  # Raw token without "Bearer " prefix
    })
    assert resp.status_code == 401


async def test_multiple_endpoints_require_auth(client):
    """All write/read endpoints that depend on require_user should return 401 without token."""
    protected_urls = [
        ("GET", "/api/cart"),
        ("POST", "/api/cart/items"),
        ("PUT", "/api/cart/items/1"),
        ("DELETE", "/api/cart/items/1"),
        ("DELETE", "/api/cart"),
        ("GET", "/api/orders"),
        ("GET", "/api/orders/1"),
        ("POST", "/api/orders"),
        ("POST", "/api/orders/1/pay"),
        ("GET", "/api/addresses"),
        ("POST", "/api/addresses"),
        ("PUT", "/api/addresses/1"),
        ("DELETE", "/api/addresses/1"),
        ("GET", "/api/user/profile"),
        ("PUT", "/api/user/profile"),
        ("DELETE", "/api/user/account"),
        ("GET", "/api/user/coupons"),
        ("POST", "/api/coupons/1/claim"),
    ]
    for method, url in protected_urls:
        if method == "GET":
            resp = await client.get(url)
        elif method == "POST":
            resp = await client.post(url, json={})
        elif method == "PUT":
            resp = await client.put(url, json={})
        elif method == "DELETE":
            resp = await client.delete(url)
        assert resp.status_code == 401, f"{method} {url} should require auth, got {resp.status_code}"


# ── JWT algorithm confusion tests ────────────────────────────────────

async def test_protected_endpoint_alg_none(client):
    """Token with alg=none (no signature) must be rejected → 401."""
    import base64
    import json

    expire = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "1", "exp": expire}).encode()
    ).rstrip(b"=").decode()
    # Unsigned token: header.payload. (trailing dot, no signature)
    none_token = f"{header}.{payload}."

    resp = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {none_token}",
    })
    assert resp.status_code == 401


async def test_protected_endpoint_algorithm_substitution(client):
    """Token claiming RS256 in header when only HS256 is allowed → 401."""
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": "1", "exp": expire}
    # Sign with HS256 secret but claim RS256 in the header
    bad_token = jwt.encode(
        payload, _SECRET, algorithm="HS256",
        headers={"alg": "RS256"},
    )

    resp = await client.get("/api/cart", headers={
        "Authorization": f"Bearer {bad_token}",
    })
    assert resp.status_code == 401


# ── WeChat login code injection tests ────────────────────────────────

async def test_login_sql_metacharacters(client):
    """Login with SQL-like code does not crash (dev mode)."""
    resp = await client.post("/api/auth/login", json={
        "code": "test'; DROP TABLE users;--",
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


async def test_login_path_traversal(client):
    """Login with path-traversal code does not crash (dev mode)."""
    resp = await client.post("/api/auth/login", json={
        "code": "../../../etc/passwd",
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


async def test_login_special_characters(client):
    """Login with special characters in code does not crash (dev mode)."""
    resp = await client.post("/api/auth/login", json={
        "code": "test\n\r\t\x00",
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


async def test_login_unicode_emoji(client):
    """Login with Unicode emoji in code does not crash (dev mode)."""
    resp = await client.post("/api/auth/login", json={
        "code": "🎉测试🚀",
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


async def test_login_very_long_code(client):
    """Login with a very long code does not crash (dev mode)."""
    resp = await client.post("/api/auth/login", json={
        "code": "x" * 10000,
    })
    assert resp.status_code == 200
    assert "token" in resp.json()


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

"""
Tests for user profile endpoints: get, update (CRUD), soft-delete account
and re-login reactivation flow.
"""

import pytest

from app.db import SessionLocal
from app.models import User


# ── Profile GET tests ─────────────────────────────────────────────────

async def test_get_profile(client, auth_headers):
    """GET /api/user/profile returns the current user's profile with masked openid."""
    headers = await auth_headers(code="profile_get_test", nickname="ProfileUser")

    resp = await client.get("/api/user/profile", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nickname"] == "ProfileUser"
    # openid should be masked with ****
    assert "****" in data["openid"]
    assert "id" in data


async def test_get_profile_no_auth(client):
    """GET /api/user/profile without auth → 401."""
    resp = await client.get("/api/user/profile")
    assert resp.status_code == 401


# ── Profile UPDATE / CRUD tests ───────────────────────────────────────

async def test_update_profile(client, auth_headers):
    """PUT /api/user/profile updates nickname; the change is reflected in subsequent GET."""
    headers = await auth_headers(code="profile_update_test", nickname="OldName")

    resp = await client.put("/api/user/profile", json={
        "nickname": "NewName",
    }, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "NewName"

    # Verify via GET
    get_resp = await client.get("/api/user/profile", headers=headers)
    assert get_resp.json()["nickname"] == "NewName"


async def test_update_profile_all_fields(client, auth_headers):
    """PUT /api/user/profile updating nickname, avatar, and phone all at once."""
    headers = await auth_headers(code="profile_full_update", nickname="OldName")

    resp = await client.put("/api/user/profile", json={
        "nickname": "FullUpdate",
        "avatar": "https://example.com/avatar.png",
        "phone": "13900001111",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nickname"] == "FullUpdate"
    assert data["avatar"] == "https://example.com/avatar.png"
    assert data["phone"] == "13900001111"

    # Verify persisted via GET
    get_resp = await client.get("/api/user/profile", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["nickname"] == "FullUpdate"
    assert get_resp.json()["avatar"] == "https://example.com/avatar.png"
    assert get_resp.json()["phone"] == "13900001111"


async def test_update_profile_empty_body(client, auth_headers):
    """PUT /api/user/profile with empty JSON body → 200, nothing changes."""
    headers = await auth_headers(code="profile_empty_update", nickname="KeepMe")

    resp = await client.put("/api/user/profile", json={}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "KeepMe"

    # GET confirms nickname unchanged
    get_resp = await client.get("/api/user/profile", headers=headers)
    assert get_resp.json()["nickname"] == "KeepMe"


async def test_update_profile_no_auth(client):
    """PUT /api/user/profile without auth → 401."""
    resp = await client.put("/api/user/profile", json={"nickname": "Hacker"})
    assert resp.status_code == 401


async def test_update_profile_partial(client, auth_headers):
    """PUT /api/user/profile only updating phone leaves nickname unchanged."""
    headers = await auth_headers(code="profile_phone_update", nickname="PhoneUser")

    resp = await client.put("/api/user/profile", json={
        "phone": "13800008888",
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nickname"] == "PhoneUser"
    assert data["phone"] == "13800008888"


# ── Account soft-delete tests ─────────────────────────────────────────

async def test_delete_account(client, auth_headers):
    """DELETE /api/user/account soft-deletes; re-login reactivates and issues a new token."""
    headers = await auth_headers(code="profile_delete_test")

    # Delete account
    resp = await client.delete("/api/user/account", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Account deleted"

    # The old token should now be rejected (user is_active=False)
    resp_blocked = await client.get("/api/user/profile", headers=headers)
    assert resp_blocked.status_code == 401

    # Re-login with same code → reactivates account, gets a new token
    login_resp = await client.post("/api/auth/login", json={
        "code": "profile_delete_test",
    })
    assert login_resp.status_code == 200
    new_token = login_resp.json()["token"]
    assert new_token  # new token issued

    # The new token should work again
    new_headers = {"Authorization": f"Bearer {new_token}"}
    profile_resp = await client.get("/api/user/profile", headers=new_headers)
    assert profile_resp.status_code == 200


async def test_delete_account_twice(client, auth_headers):
    """Soft-deleting an already-deleted account → 200 (idempotent)."""
    headers = await auth_headers(code="delete_twice_test")

    # First delete
    resp1 = await client.delete("/api/user/account", headers=headers)
    assert resp1.status_code == 200

    # Token is now invalid, so second DELETE with same token should 401
    resp2 = await client.delete("/api/user/account", headers=headers)
    assert resp2.status_code == 401

    # But re-login + delete again should succeed (deleted→reactivated→deleted)
    login_resp = await client.post("/api/auth/login", json={"code": "delete_twice_test"})
    new_headers = {"Authorization": f"Bearer {login_resp.json()['token']}"}
    resp3 = await client.delete("/api/user/account", headers=new_headers)
    assert resp3.status_code == 200


async def test_soft_delete_blocks_all_endpoints(client, auth_headers):
    """After soft-delete, old token is blocked on all protected endpoints."""
    headers = await auth_headers(code="delete_blocks_all")

    # Add something to cart first so we have state
    await client.post("/api/cart/items", json={
        "product_id": 1, "quantity": 1,
    }, headers=headers)

    # Delete account
    del_resp = await client.delete("/api/user/account", headers=headers)
    assert del_resp.status_code == 200

    # All protected endpoints should return 401 with the old token
    endpoints = [
        ("GET", "/api/cart"),
        ("GET", "/api/orders"),
        ("GET", "/api/user/coupons"),
        ("PUT", "/api/user/profile"),
        ("DELETE", "/api/user/account"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = await client.get(path, headers=headers)
        elif method == "PUT":
            resp = await client.put(path, headers=headers, json={})
        elif method == "DELETE":
            resp = await client.delete(path, headers=headers)
        assert resp.status_code == 401, f"{method} {path} should be 401 after soft-delete, got {resp.status_code}"


# ── Re-login reactivation tests ───────────────────────────────────────

async def test_relogin_reactivates_same_user(client, auth_headers):
    """After soft-delete, re-login reactivates the same user (same id), not a new one."""
    # Create + get user id
    login1 = await client.post("/api/auth/login", json={
        "code": "same_user_test",
        "nickname": "SameUser",
    })
    original_user_id = login1.json()["user_id"]
    original_headers = {"Authorization": f"Bearer {login1.json()['token']}"}

    # Soft-delete
    await client.delete("/api/user/account", headers=original_headers)

    # Re-login
    login2 = await client.post("/api/auth/login", json={"code": "same_user_test"})
    assert login2.status_code == 200
    assert login2.json()["user_id"] == original_user_id, (
        "Re-login should reactivate the same user, not create a new one"
    )

    # Also verify is_active is True in DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == original_user_id).first()
        assert user is not None
        assert user.is_active is True
    finally:
        db.close()


async def test_relogin_updates_profile_on_reactivation(client, auth_headers):
    """Re-login after soft-delete with new nickname/avatar updates the profile."""
    # Create user with initial profile
    login1 = await client.post("/api/auth/login", json={
        "code": "react_update_test",
        "nickname": "OriginalNick",
        "avatar": "https://old.avatar/url",
    })
    user_id = login1.json()["user_id"]
    headers1 = {"Authorization": f"Bearer {login1.json()['token']}"}

    # Verify initial profile
    profile1 = await client.get("/api/user/profile", headers=headers1)
    assert profile1.json()["nickname"] == "OriginalNick"
    assert profile1.json()["avatar"] == "https://old.avatar/url"

    # Soft-delete
    await client.delete("/api/user/account", headers=headers1)

    # Re-login with updated profile info
    login2 = await client.post("/api/auth/login", json={
        "code": "react_update_test",
        "nickname": "ReActivatedNick",
        "avatar": "https://new.avatar/url",
    })
    assert login2.status_code == 200
    assert login2.json()["user_id"] == user_id  # same user
    assert login2.json()["nickname"] == "ReActivatedNick"

    # Verify profile is updated
    new_headers = {"Authorization": f"Bearer {login2.json()['token']}"}
    profile2 = await client.get("/api/user/profile", headers=new_headers)
    assert profile2.json()["nickname"] == "ReActivatedNick"
    assert profile2.json()["avatar"] == "https://new.avatar/url"


async def test_multiple_delete_relogin_cycles(client):
    """Multiple delete + re-login cycles should work correctly."""
    code = "cycle_test_user"
    first_user_id = None
    for cycle in range(3):
        # Login (or re-login after cycle 0)
        login = await client.post("/api/auth/login", json={"code": code})
        assert login.status_code == 200, f"Cycle {cycle}: login failed"
        token = login.json()["token"]
        user_id = login.json()["user_id"]

        # All cycles should return the same user (reactivation, not recreation)
        if first_user_id is None:
            first_user_id = user_id
        else:
            assert user_id == first_user_id, (
                f"Cycle {cycle}: re-login should reactivate the same user "
                f"(expected id={first_user_id}, got id={user_id})"
            )

        # Verify access works (confirms the account is active)
        headers = {"Authorization": f"Bearer {token}"}
        profile = await client.get("/api/user/profile", headers=headers)
        assert profile.status_code == 200, f"Cycle {cycle}: profile access failed"

        # Soft-delete
        delete = await client.delete("/api/user/account", headers=headers)
        assert delete.status_code == 200, f"Cycle {cycle}: delete failed"

        # Token should be invalid now (account is inactive)
        blocked = await client.get("/api/user/profile", headers=headers)
        assert blocked.status_code == 401, f"Cycle {cycle}: token not blocked after delete"


async def test_relogin_preserves_phone_on_reactivation(client, auth_headers):
    """Re-login after soft-delete preserves the phone number that was set before deletion."""
    headers = await auth_headers(code="preserve_phone_test")

    # Set phone via profile update
    await client.put("/api/user/profile", json={
        "phone": "13600009999",
    }, headers=headers)

    # Soft-delete
    await client.delete("/api/user/account", headers=headers)

    # Re-login (without passing phone — the API doesn't accept phone on login anyway)
    login = await client.post("/api/auth/login", json={"code": "preserve_phone_test"})
    new_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    # Phone should still be there
    profile = await client.get("/api/user/profile", headers=new_headers)
    assert profile.status_code == 200
    assert profile.json()["phone"] == "13600009999"


# ── OpenID masking edge cases ─────────────────────────────────────────

async def test_profile_masked_openid_short(client, auth_headers):
    """A short openid (<=8 chars) uses compact masking: first 2 + **** + last 2."""
    # Dev mode creates openid = "wx_" + code, so use a 3-char code to get
    # openid "wx_abc" (6 chars, which is <= 8 → short masking path).
    login = await client.post("/api/auth/login", json={
        "code": "abc",
        "nickname": "ShortMask",
    })
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    profile = await client.get("/api/user/profile", headers=headers)
    assert profile.status_code == 200
    # "wx_abc" (6 chars <= 8): first 2 + **** + last 2 = "wx****bc"
    assert profile.json()["openid"] == "wx****bc"


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

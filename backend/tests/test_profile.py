"""
Tests for user profile endpoints: get, update, soft-delete account.
"""

import pytest


# ── Profile tests ─────────────────────────────────────────────────────

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


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

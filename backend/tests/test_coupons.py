"""
Tests for coupon endpoints: list available, claim, duplicate claim rejection.
"""

import pytest


# ── Coupon tests ──────────────────────────────────────────────────────

async def test_list_coupons(client):
    """GET /api/coupons (no auth) returns available coupons."""
    resp = await client.get("/api/coupons")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Each coupon should have required fields
    for c in data:
        assert "id" in c
        assert "name" in c
        assert "type" in c
        assert "value" in c


async def test_claim_coupon(client, auth_headers):
    """POST /api/coupons/1/claim (auth required) claims a coupon successfully."""
    headers = await auth_headers(code="coupon_claim_test")
    resp = await client.post("/api/coupons/1/claim", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Coupon claimed"

    # Verify the claimed coupon appears in user's coupon list
    user_coupons = await client.get("/api/user/coupons", headers=headers)
    assert user_coupons.status_code == 200
    uc_data = user_coupons.json()
    assert isinstance(uc_data, list)
    assert len(uc_data) == 1
    assert uc_data[0]["status"] == "unused"
    assert uc_data[0]["template"]["id"] == 1


async def test_claim_duplicate(client, auth_headers):
    """Claiming the same coupon twice → 400 on second attempt."""
    headers = await auth_headers(code="coupon_dup_test")

    # First claim succeeds
    resp1 = await client.post("/api/coupons/2/claim", headers=headers)
    assert resp1.status_code == 200

    # Second claim fails
    resp2 = await client.post("/api/coupons/2/claim", headers=headers)
    assert resp2.status_code == 400
    assert "already claimed" in resp2.json()["detail"].lower()


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

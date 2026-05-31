"""
Tests for coupon endpoints: list available, claim, duplicate rejection,
expiry handling, auto-expire on list, used_count tracking.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import CouponTemplate, UserCoupon, CouponStatus


# ── Basic coupon tests (existing) ─────────────────────────────────────

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


# ── Coupon expiry tests ───────────────────────────────────────────────

async def test_claim_coupon_expired(client, auth_headers):
    """Claiming a coupon whose end_time is in the past → 400."""
    headers = await auth_headers(code="coupon_expired_test")

    # Directly set template #1 end_time to 1 hour ago
    db = SessionLocal()
    try:
        template = db.query(CouponTemplate).filter(CouponTemplate.id == 1).first()
        template.end_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    resp = await client.post("/api/coupons/1/claim", headers=headers)
    assert resp.status_code == 400
    assert "not available" in resp.json()["detail"].lower()


async def test_claim_coupon_not_started(client, auth_headers):
    """Claiming a coupon whose start_time is in the future → 400."""
    headers = await auth_headers(code="coupon_future_test")

    # Set template #1 start_time to 1 hour from now, end_time far future
    db = SessionLocal()
    try:
        template = db.query(CouponTemplate).filter(CouponTemplate.id == 1).first()
        template.start_time = datetime.now(timezone.utc) + timedelta(hours=1)
        template.end_time = datetime.now(timezone.utc) + timedelta(days=365)
        db.commit()
    finally:
        db.close()

    resp = await client.post("/api/coupons/1/claim", headers=headers)
    assert resp.status_code == 400
    assert "not available" in resp.json()["detail"].lower()


async def test_claim_coupon_fully_claimed(client, auth_headers):
    """Claiming a coupon that has reached its total_count → 400."""
    # Set total_count and used_count to 1
    db = SessionLocal()
    try:
        template = db.query(CouponTemplate).filter(CouponTemplate.id == 1).first()
        template.total_count = 1
        template.used_count = 1  # already exhausted
        db.commit()
    finally:
        db.close()

    headers = await auth_headers(code="coupon_exhausted_test")
    resp = await client.post("/api/coupons/1/claim", headers=headers)
    assert resp.status_code == 400
    assert "fully claimed" in resp.json()["detail"].lower()


# ── Coupon auth / 404 tests ───────────────────────────────────────────

async def test_claim_coupon_no_auth(client):
    """POST /api/coupons/1/claim without auth → 401."""
    resp = await client.post("/api/coupons/1/claim")
    assert resp.status_code == 401


async def test_claim_coupon_404(client, auth_headers):
    """POST /api/coupons/9999/claim (non-existent) → 404."""
    headers = await auth_headers(code="coupon_404_test")
    resp = await client.post("/api/coupons/9999/claim", headers=headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ── User coupon listing + auto-expiry ─────────────────────────────────

async def test_user_coupons_used_status_persists(client, auth_headers):
    """A USED coupon should NOT be re-classified as EXPIRED even if end_time is past."""
    # Get user_id from login so we can filter precisely
    login_resp = await client.post("/api/auth/login", json={
        "code": "used_coupon_user",
        "nickname": "Tester",
    })
    assert login_resp.status_code == 200
    user_id = login_resp.json()["user_id"]
    headers = {"Authorization": f"Bearer {login_resp.json()['token']}"}

    # Claim coupon #1
    claim_resp = await client.post("/api/coupons/1/claim", headers=headers)
    assert claim_resp.status_code == 200

    # Manually mark the UserCoupon as USED (simulating order usage)
    db = SessionLocal()
    try:
        uc = db.query(UserCoupon).filter(
            UserCoupon.user_id == user_id
        ).first()
        assert uc is not None, "Should have found the test user's coupon"
        uc.status = CouponStatus.USED
        db.commit()

        # Also set template end_time to past
        template = db.query(CouponTemplate).filter(CouponTemplate.id == 1).first()
        if template:
            template.end_time = datetime.now(timezone.utc) - timedelta(hours=1)
            db.commit()
    finally:
        db.close()

    # Listing should show status=used (NOT expired)
    uc_resp = await client.get("/api/user/coupons", headers=headers)
    assert uc_resp.status_code == 200
    data = uc_resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "used", (
        f"Used coupon should stay 'used' even after expiry. Got: {data[0]['status']}"
    )


async def test_user_coupons_mixed_statuses(client, auth_headers):
    """User with multiple coupons should see each with its proper status."""
    # Get user_id from login so we can filter precisely
    login_resp = await client.post("/api/auth/login", json={
        "code": "mixed_status_user",
        "nickname": "Tester",
    })
    assert login_resp.status_code == 200
    user_id = login_resp.json()["user_id"]
    headers = {"Authorization": f"Bearer {login_resp.json()['token']}"}

    # Claim coupon #1
    r1 = await client.post("/api/coupons/1/claim", headers=headers)
    assert r1.status_code == 200

    # Claim coupon #2
    r2 = await client.post("/api/coupons/2/claim", headers=headers)
    assert r2.status_code == 200

    # Manually set coupon #1's UserCoupon to USED and its template's end_time to past
    db = SessionLocal()
    try:
        # Filter by the test user's ID and order by id for deterministic results
        uc_list = db.query(UserCoupon).filter(
            UserCoupon.user_id == user_id
        ).order_by(UserCoupon.id).all()
        assert len(uc_list) == 2
        uc_list[0].status = CouponStatus.USED

        # Mark second coupon's template as expired
        template2 = db.query(CouponTemplate).filter(CouponTemplate.id == 2).first()
        template2.end_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    # List should show: one USED, one EXPIRED (auto-expired on list)
    uc_resp = await client.get("/api/user/coupons", headers=headers)
    assert uc_resp.status_code == 200
    data = uc_resp.json()
    assert len(data) == 2

    statuses = {c["template"]["id"]: c["status"] for c in data}
    assert statuses[1] == "used", f"Coupon #1 should be 'used', got {statuses.get(1)}"
    assert statuses[2] == "expired", f"Coupon #2 should be 'expired' (auto-expired), got {statuses.get(2)}"


async def test_user_coupons_auto_expire(client, auth_headers):
    """Listing user coupons with an expired template → status becomes 'expired'."""
    headers = await auth_headers(code="coupon_auto_expire_test")

    # Claim coupon #1 (currently valid)
    claim_resp = await client.post("/api/coupons/1/claim", headers=headers)
    assert claim_resp.status_code == 200

    # Verify status is "unused" initially
    uc1 = await client.get("/api/user/coupons", headers=headers)
    assert uc1.status_code == 200
    uc1_data = uc1.json()
    assert len(uc1_data) == 1
    assert uc1_data[0]["status"] == "unused"

    # Set the coupon template end_time to 1 hour in the past
    db = SessionLocal()
    try:
        template = db.query(CouponTemplate).filter(CouponTemplate.id == 1).first()
        template.end_time = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    # Listing user coupons again → status should auto-transition to "expired"
    uc2 = await client.get("/api/user/coupons", headers=headers)
    assert uc2.status_code == 200
    uc2_data = uc2.json()
    assert len(uc2_data) == 1
    assert uc2_data[0]["status"] == "expired"

    # Verify the status is persisted (second list call still shows "expired")
    uc3 = await client.get("/api/user/coupons", headers=headers)
    assert uc3.status_code == 200
    assert uc3.json()[0]["status"] == "expired"


# ── used_count tracking ──────────────────────────────────────────────

async def test_claim_coupon_increments_used_count(client, auth_headers):
    """Each claim increments used_count on the template."""
    # Set a higher total so we can claim multiple times
    db = SessionLocal()
    try:
        template = db.query(CouponTemplate).filter(CouponTemplate.id == 1).first()
        template.total_count = 100
        template.used_count = 0
        db.commit()
    finally:
        db.close()

    # First user claims
    headers_a = await auth_headers(code="count_user_a")
    resp_a = await client.post("/api/coupons/1/claim", headers=headers_a)
    assert resp_a.status_code == 200

    # Second user claims
    headers_b = await auth_headers(code="count_user_b")
    resp_b = await client.post("/api/coupons/1/claim", headers=headers_b)
    assert resp_b.status_code == 200

    # Verify used_count is 2
    db2 = SessionLocal()
    try:
        template = db2.query(CouponTemplate).filter(CouponTemplate.id == 1).first()
        assert template.used_count == 2
    finally:
        db2.close()


# ── Exhausted coupon not in available list ────────────────────────────

async def test_fully_claimed_coupon_not_listed(client):
    """A fully-claimed coupon does not appear in GET /api/coupons."""
    db = SessionLocal()
    try:
        template = db.query(CouponTemplate).filter(CouponTemplate.id == 1).first()
        template.total_count = 1
        template.used_count = 1
        db.commit()
    finally:
        db.close()

    resp = await client.get("/api/coupons")
    assert resp.status_code == 200
    data = resp.json()
    ids = [c["id"] for c in data]
    assert 1 not in ids, "Fully claimed coupon should not appear in available list"


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

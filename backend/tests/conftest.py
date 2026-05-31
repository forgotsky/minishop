"""
Shared pytest fixtures for MiniShop backend tests.

Uses SQLite file-based database for testing.
Sets DATABASE_URL env var BEFORE importing app modules so the engine
is created against the test database.

Database lifecycle:
- Tables are created once per test module (scope="module").
- Data is reset (deleted + re-seeded) between every test function.
- This avoids DDL race conditions that occur when drop_all/create_all
  interleave with async tests under asyncio_mode=auto.
"""

import os
import sys
from datetime import timezone

# ── Must set env vars BEFORE importing app modules ──────────────────────
TEST_DIR = os.path.dirname(os.path.abspath(__file__))       # backend/tests/
BACKEND_DIR = os.path.dirname(TEST_DIR)                      # backend/
TEST_DB = os.path.join(BACKEND_DIR, "test.db")

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["RUN_MODE"] = "dev"

# Ensure backend is on sys.path
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
import httpx
from sqlalchemy import event

from app.main import app
from app.db import SessionLocal, Base, engine, get_db
from app.models import (
    Product, CouponTemplate,
    CartItem, Order, OrderItem, Address, User, UserCoupon,
)


# ── SQLite datetime fix ────────────────────────────────────────────────
# SQLite strips timezone info from DateTime(timezone=True) columns.
# The coupon claim endpoint compares template.start_time / end_time
# against datetime.now(timezone.utc), which is offset-aware.
# This listener re-attaches UTC tzinfo so the comparison succeeds.

@event.listens_for(CouponTemplate, "load")
def _fix_coupon_timezone(template, context):
    """Re-attach UTC timezone to coupon datetimes loaded from SQLite."""
    if template.start_time is not None and template.start_time.tzinfo is None:
        template.start_time = template.start_time.replace(tzinfo=timezone.utc)
    if template.end_time is not None and template.end_time.tzinfo is None:
        template.end_time = template.end_time.replace(tzinfo=timezone.utc)


# ── Override FastAPI dependency ────────────────────────────────────────

def override_get_db():
    """Provide test database session via FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ── Module-scoped table creation (once per test file) ──────────────────
# Tables persist across tests; only data is reset between functions.

@pytest.fixture(scope="module", autouse=True)
def create_tables():
    """Create all tables once per test module."""
    Base.metadata.create_all(bind=engine)
    yield
    # Tables remain for the duration of the module (dropped by cleanup)


# ── Function-scoped data reset ─────────────────────────────────────────
# Each test gets fresh seed data; cross-test contamination is prevented
# by deleting all rows from every table before re-seeding.

@pytest.fixture(scope="function", autouse=True)
def reset_data():
    """Delete all data and re-seed between test functions."""
    db = SessionLocal()
    try:
        # Delete child tables first to respect foreign keys
        for model in [OrderItem, Order, CartItem, Address, UserCoupon, User, CouponTemplate, Product]:
            db.query(model).delete()
        db.commit()

        from app.main import seed_products, seed_coupons
        seed_products(db)
        seed_coupons(db)
        db.commit()
    finally:
        db.close()

    yield


# ── Session-scoped database file cleanup ───────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def cleanup_db_file():
    """Drop all tables and delete test database file after all tests complete."""
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        os.remove(TEST_DB)
    except (FileNotFoundError, PermissionError):
        pass


# ── Function-scoped client fixtures ────────────────────────────────────

@pytest.fixture
async def client():
    """Async HTTP client backed by the FastAPI app (ASGI transport)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client):
    """
    Factory fixture: returns a callable that logs in a user and returns
    an ``Authorization`` header dict.

    Usage in tests::

        headers = await auth_headers(code="my_test_code")
        resp = await client.get("/api/cart", headers=headers)
    """

    async def _auth_headers(code="test_code", nickname="Tester"):
        resp = await client.post("/api/auth/login", json={
            "code": code,
            "nickname": nickname,
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers

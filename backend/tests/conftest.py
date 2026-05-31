"""
Shared pytest fixtures for MiniShop backend tests.

Uses SQLite file-based database for testing.
Sets DATABASE_URL env var BEFORE importing app modules so the engine
is created against the test database.
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
from app.models import Product, CouponTemplate


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


# ── Function-scoped database setup / teardown ──────────────────────────
# Each test gets fresh tables and seed data to avoid cross-test contamination.


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create all tables and seed data fresh for each test function."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        from app.main import seed_products, seed_coupons
        if db.query(Product).count() == 0:
            seed_products(db)
        if db.query(CouponTemplate).count() == 0:
            seed_coupons(db)
    finally:
        db.close()

    yield

    # Drop all tables so the next test gets a clean slate
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def cleanup_db_file():
    """Delete test database file after all tests complete."""
    yield
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

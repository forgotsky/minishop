"""
Smoke tests for health-check and hello endpoints.
These are public (no auth required) endpoints.
"""

import pytest


async def test_health_returns_ok(client):
    """GET /api/health → 200 with {"status":"ok"}."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_hello_returns_message(client):
    """GET /api/hello → 200 with {"message":"Hello, World!"}."""
    resp = await client.get("/api/hello")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"message": "Hello, World!"}


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__])

"""Smoke test for the FastAPI app: the /health endpoint and security headers.

Uses TestClient without the context-manager form so startup/shutdown events
(which touch external storage) are not triggered.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_ok():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"


def test_security_headers_present():
    res = client.get("/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "Referrer-Policy" in res.headers

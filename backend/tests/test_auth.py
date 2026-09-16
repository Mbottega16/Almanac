from app.config import settings


def test_auth_status_open_when_gate_dormant(client):
    resp = client.get("/api/auth-status")
    assert resp.status_code == 200
    assert resp.json() == {"gate_enabled": False}


def test_auth_status_open_when_gate_active(client, monkeypatch):
    """auth-status must stay open even with the gate on — it's how an
    unauthenticated frontend decides whether to show LoginGate. If this ever
    401s, App.tsx's fetchAuthStatus() throws before it can read gate_enabled,
    and its catch-all falls back to "authed = true" without ever showing the
    login screen (production incident, 2026-09-16)."""
    monkeypatch.setattr(settings, "admin_password", "test-password")
    resp = client.get("/api/auth-status")
    assert resp.status_code == 200
    assert resp.json() == {"gate_enabled": True}


def test_protected_route_still_requires_login_when_gate_active(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "test-password")
    resp = client.get("/api/resources")
    assert resp.status_code == 401


def test_login_then_protected_route_works(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "test-password")
    login = client.post("/api/login", json={"password": "test-password"})
    assert login.status_code == 200
    resp = client.get("/api/resources")
    assert resp.status_code == 200


def test_wrong_password_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "test-password")
    login = client.post("/api/login", json={"password": "wrong"})
    assert login.status_code == 401

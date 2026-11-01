from app import auth
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


def test_login_cookie_carries_the_session_lifetime(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "test-password")
    login = client.post("/api/login", json={"password": "test-password"})
    assert f"Max-Age={auth.SESSION_MAX_AGE}" in login.headers["set-cookie"]


def test_session_token_is_valid_until_it_expires():
    token = auth.issue_cookie_value()
    assert auth._cookie_is_valid(token) is True
    # A token older than the allowed age is refused even though its signature is good.
    assert auth._cookie_is_valid(token, max_age=-1) is False


def test_token_signed_with_another_secret_is_refused():
    from itsdangerous import URLSafeTimedSerializer

    forged = URLSafeTimedSerializer("not-the-real-secret", salt="almanac-auth").dumps({"ok": True})
    assert auth._cookie_is_valid(forged) is False


def test_tampered_token_is_refused():
    token = auth.issue_cookie_value()
    body, sig = token.rsplit(".", 1)
    # Flip the last character of the signature; the payload is untouched.
    flipped = sig[:-1] + ("A" if sig[-1] != "A" else "B")
    assert auth._cookie_is_valid(f"{body}.{flipped}") is False


def test_forged_cookie_gets_401_from_the_api(client, monkeypatch):
    from itsdangerous import URLSafeTimedSerializer

    monkeypatch.setattr(settings, "admin_password", "test-password")
    forged = URLSafeTimedSerializer("not-the-real-secret", salt="almanac-auth").dumps({"ok": True})
    client.cookies.set(auth.COOKIE_NAME, forged)
    assert client.get("/api/resources").status_code == 401


def test_expired_session_is_rejected_by_the_api(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "test-password")
    client.post("/api/login", json={"password": "test-password"})
    # Lifetime shrunk to nothing: the cookie is still signed, but it is too old now.
    monkeypatch.setattr(auth, "SESSION_MAX_AGE", -1)
    assert client.get("/api/resources").status_code == 401

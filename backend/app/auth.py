"""Optional whole-app auth gate.

Dormant by default: if ADMIN_PASSWORD is unset, every request passes through
untouched (this is how the app runs locally and how the first deploy runs,
matching Atlas). Set ADMIN_PASSWORD (and ideally ADMIN_SESSION_SECRET) and
the gate activates — every route except the always-open allowlist then needs
a valid signed session cookie, obtained by POSTing the password to
/api/login.
"""
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

COOKIE_NAME = "almanac_session"
# The token itself expires, not just the browser cookie: a copied cookie
# stops working after this many seconds even if it is replayed.
SESSION_MAX_AGE = 60 * 60 * 24 * 30
# Requests to these paths are always allowed, gate or no gate.
# auth-status must stay open: it's how an unauthenticated frontend decides
# whether to show LoginGate. If it 401s, fetchAuthStatus() throws before the
# frontend ever reads gate_enabled, and App.tsx's catch-all falls back to
# "authed = true" without ever showing the login screen.
OPEN_PATHS = {"/api/health", "/api/login", "/api/auth-status", "/docs", "/openapi.json", "/redoc"}


def _serializer() -> URLSafeTimedSerializer:
    secret = settings.admin_session_secret or settings.admin_password or "almanac-dev"
    return URLSafeTimedSerializer(secret, salt="almanac-auth")


def issue_cookie_value() -> str:
    return _serializer().dumps({"ok": True})


def _cookie_is_valid(raw: str | None, max_age: int | None = None) -> bool:
    if not raw:
        return False
    # Tokens issued before the timestamp was added have no signed time, so
    # they fail here and the owner signs in once more.
    try:
        age = SESSION_MAX_AGE if max_age is None else max_age
        return bool(_serializer().loads(raw, max_age=age).get("ok"))
    except BadSignature:  # includes SignatureExpired
        return False


class AuthGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.admin_password:
            return await call_next(request)  # gate dormant
        path = request.url.path
        if path in OPEN_PATHS or not path.startswith("/api"):
            return await call_next(request)
        if _cookie_is_valid(request.cookies.get(COOKIE_NAME)):
            return await call_next(request)
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

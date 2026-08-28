"""Optional whole-app auth gate.

Dormant by default: if ADMIN_PASSWORD is unset, every request passes through
untouched (this is how the app runs locally and how the first deploy runs,
matching Atlas). Set ADMIN_PASSWORD (and ideally ADMIN_SESSION_SECRET) and
the gate activates — every route except the always-open allowlist then needs
a valid signed session cookie, obtained by POSTing the password to
/api/login.
"""
from itsdangerous import BadSignature, URLSafeSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

COOKIE_NAME = "almanac_session"
# Requests to these paths are always allowed, gate or no gate.
OPEN_PATHS = {"/api/health", "/api/login", "/docs", "/openapi.json", "/redoc"}


def _serializer() -> URLSafeSerializer:
    secret = settings.admin_session_secret or settings.admin_password or "almanac-dev"
    return URLSafeSerializer(secret, salt="almanac-auth")


def issue_cookie_value() -> str:
    return _serializer().dumps({"ok": True})


def _cookie_is_valid(raw: str | None) -> bool:
    if not raw:
        return False
    try:
        return bool(_serializer().loads(raw).get("ok"))
    except BadSignature:
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

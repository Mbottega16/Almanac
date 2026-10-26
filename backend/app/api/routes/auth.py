from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.auth import COOKIE_NAME, SESSION_MAX_AGE, issue_cookie_value
from app.config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


class AuthStatus(BaseModel):
    # gate_enabled=False -> the app is open, no login needed
    gate_enabled: bool


@router.get("/auth-status", response_model=AuthStatus)
def auth_status():
    return AuthStatus(gate_enabled=bool(settings.admin_password))


@router.post("/login")
def login(body: LoginRequest, response: Response):
    if not settings.admin_password:
        return {"ok": True, "note": "auth gate is not enabled"}
    if body.password != settings.admin_password:
        response.status_code = 401
        return {"detail": "Wrong password"}
    # SameSite=None; Secure so the cookie survives the cross-site hop from the
    # Vercel frontend to the Vercel backend when the gate is enabled.
    response.set_cookie(
        COOKIE_NAME,
        issue_cookie_value(),
        httponly=True,
        samesite="none",
        secure=True,
        max_age=SESSION_MAX_AGE,
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}

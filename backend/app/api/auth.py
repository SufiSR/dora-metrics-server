from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import require_admin_session
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, UserRole

router = APIRouter()
AdminSessionDep = Annotated[None, Depends(require_admin_session)]


def _admin_login_ok(username: str, password: str) -> bool:
    expected_user = (os.getenv("DORA_ADMIN_USERNAME") or "admin").strip()
    expected_password = (os.getenv("DORA_ADMIN_PASSWORD") or "").strip()
    if not expected_password:
        return False
    try:
        user_ok = secrets.compare_digest(
            username.encode("utf-8"), expected_user.encode("utf-8")
        )
        pass_ok = secrets.compare_digest(
            password.encode("utf-8"), expected_password.encode("utf-8")
        )
    except (AttributeError, TypeError):
        return False
    return bool(user_ok and pass_ok)


@router.post("/login", response_model=LoginResponse)
def login(request: Request, body: LoginRequest) -> LoginResponse:
    if not _admin_login_ok(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    request.session.clear()
    request.session["admin"] = True
    request.session["username"] = body.username
    return LoginResponse(role=UserRole.ADMIN, expires_at=None)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, _auth: AdminSessionDep) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(request: Request) -> MeResponse:
    if request.session.get("admin"):
        username = request.session.get("username")
        return MeResponse(
            role=UserRole.ADMIN,
            username=str(username) if username is not None else None,
        )
    return MeResponse(role=None, username=None)

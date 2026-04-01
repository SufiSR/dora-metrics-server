from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    ADMIN = "admin"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    role: UserRole
    expires_at: datetime | None = None


class MeResponse(BaseModel):
    role: UserRole | None = None
    username: str | None = None

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config_schema import ConfigurationSchema
from app.database import SessionLocal
from app.services.config_service import load_runtime_config


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin_session(request: Request) -> None:
    if not request.session.get("admin"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid admin session is required",
        )


DbSession = Annotated[Session, Depends(get_db)]
SessionDep = DbSession


def get_runtime_settings(db: DbSession) -> ConfigurationSchema:
    return load_runtime_config(db=db).settings


RuntimeSettingsDep = Annotated[ConfigurationSchema, Depends(get_runtime_settings)]

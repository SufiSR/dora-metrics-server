from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, LargeBinary, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AppConfiguration(Base):
    __tablename__ = "app_configuration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    settings_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    gitlab_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    jira_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

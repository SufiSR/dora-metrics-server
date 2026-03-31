from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Release(Base):
    __tablename__ = "release"
    __table_args__ = (
        Index("ix_release_repository_committed_at", "repository_id", "committed_at"),
        Index("ix_release_customer_committed_at", "customer_release", "committed_at"),
        Index("ix_release_repo_tag_unique", "repository_id", "tag_name", unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("repository.id"), nullable=False, index=True
    )
    tag_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_major: Mapped[int | None] = mapped_column(Integer)
    version_minor: Mapped[int | None] = mapped_column(Integer)
    version_patch: Mapped[int | None] = mapped_column(Integer)
    pre_release: Mapped[str | None] = mapped_column(String(50))
    customer_release: Mapped[bool] = mapped_column(Boolean, nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

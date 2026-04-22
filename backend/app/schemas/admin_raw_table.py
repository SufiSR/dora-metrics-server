from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.releases import OffsetPagination


class RawTableColumn(BaseModel):
    key: str
    label: str
    sortable: bool = True


class RawTableResponse(BaseModel):
    table: str
    columns: list[RawTableColumn]
    rows: list[dict[str, Any]]
    pagination: OffsetPagination

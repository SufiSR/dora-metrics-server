from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: str
    last_successful_connection: datetime | None = None


class HealthResponse(BaseModel):
    status: str
    components: dict[str, ComponentHealth]

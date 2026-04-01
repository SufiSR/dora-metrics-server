from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import SessionLocal
from app.scheduler import start_scheduler, stop_scheduler
from app.services.config_service import load_runtime_config


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        config = load_runtime_config(db=db).settings
    start_scheduler(config)
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="DORA Metrics Backend", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

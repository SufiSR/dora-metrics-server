from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import SessionDep
from app.models.repository import Repository
from app.schemas.metrics import CurrentMetricsResponse, HistoryResponse, PeriodType
from app.services.metrics_public_service import (
    build_current_metrics_response,
    build_history_response,
)

router = APIRouter()


@router.get("/current", response_model=CurrentMetricsResponse)
def get_metrics_current(
    db: SessionDep,
    period_type: PeriodType = PeriodType.WEEK,
) -> CurrentMetricsResponse:
    return build_current_metrics_response(db, repository_id=None, period_type=period_type.value)


@router.get("/history", response_model=HistoryResponse)
def get_metrics_history(
    db: SessionDep,
    period_type: PeriodType = PeriodType.WEEK,
    from_: Annotated[
        date | None,
        Query(alias="from", description="Start date (ISO); default 12 weeks before `to`"),
    ] = None,
    to: Annotated[
        date | None,
        Query(description="End date (ISO); default today UTC"),
    ] = None,
    repository_id: Annotated[int | None, Query()] = None,
    page: Annotated[int, Query(ge=0)] = 0,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> HistoryResponse:
    if to is None:
        to = datetime.now(timezone.utc).date()
    if from_ is None:
        from_ = to - timedelta(weeks=12)
    if from_ > to:
        raise HTTPException(status_code=400, detail="Parameter 'from' must be on or before 'to'")
    return build_history_response(
        db,
        period_type=period_type,
        from_date=from_,
        to_date=to,
        repository_id=repository_id,
        page=page,
        size=size,
    )


@router.get("/repository/{repository_id}", response_model=CurrentMetricsResponse)
def get_metrics_for_repository(
    repository_id: int,
    db: SessionDep,
    period_type: PeriodType = PeriodType.WEEK,
) -> CurrentMetricsResponse:
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(
            status_code=404,
            detail=f"Repository with id {repository_id} not found",
        )
    return build_current_metrics_response(
        db, repository_id=repository_id, period_type=period_type.value
    )

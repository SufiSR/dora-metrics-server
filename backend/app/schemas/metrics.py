from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Trend(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class PerformanceLevel(str, Enum):
    ELITE = "ELITE"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PeriodType(str, Enum):
    WEEK = "WEEK"
    MONTH = "MONTH"
    QUARTER = "QUARTER"


class MetricValue(BaseModel):
    value: float | None
    unit: str
    display_value: str | None = None
    trend: Trend | None = None
    trend_percentage: float | None = None
    performance_level: PerformanceLevel | None = None


class CurrentMetricsResponse(BaseModel):
    deployment_frequency: MetricValue
    lead_time: MetricValue
    change_failure_rate: MetricValue
    mttr: MetricValue
    overall_performance_level: PerformanceLevel | None
    period_start: date
    period_end: date
    repository_count: int
    generated_at: datetime
    mttr_alpha: MetricValue | None = None
    release_wait_time: MetricValue | None = None


class PerformanceLevels(BaseModel):
    overall: PerformanceLevel | None
    deployment_frequency: PerformanceLevel | None
    lead_time: PerformanceLevel | None
    change_failure_rate: PerformanceLevel | None
    mttr: PerformanceLevel | None


class HistoryDataPoint(BaseModel):
    period_start: date
    period_end: date
    deployment_frequency: float | None
    lead_time_minutes: int | None
    change_failure_rate: float | None
    mttr_minutes: int | None
    mttr_alpha_minutes: int | None = None
    release_wait_median_minutes: int | None = None
    performance_level: PerformanceLevels


class Pagination(BaseModel):
    page: int
    size: int
    total_elements: int
    total_pages: int
    has_next: bool
    has_previous: bool


class HistoryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    period_type: PeriodType
    from_date: date = Field(validation_alias="from", serialization_alias="from")
    to_date: date = Field(validation_alias="to", serialization_alias="to")
    repository_id: int | None
    data: list[HistoryDataPoint]
    pagination: Pagination

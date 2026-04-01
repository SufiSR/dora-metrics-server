from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.metric_snapshot import MetricSnapshot
from app.schemas.metrics import (
    CurrentMetricsResponse,
    HistoryDataPoint,
    HistoryResponse,
    MetricValue,
    Pagination,
    PerformanceLevel,
    PerformanceLevels,
    PeriodType,
    Trend,
)
from app.services.metric_service import classify_performance_level


def _mean_float_from_decimal(values: list[Decimal | None]) -> float | None:
    xs = [float(v) for v in values if v is not None]
    if not xs:
        return None
    return sum(xs) / len(xs)


def _median_int(values: list[int | None]) -> int | None:
    xs = [v for v in values if v is not None]
    if not xs:
        return None
    return int(median(xs))


def _minutes_display(minutes: int | None) -> str | None:
    if minutes is None:
        return None
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 24 * 60:
        h = minutes // 60
        return f"{h} hour" + ("s" if h != 1 else "")
    d = minutes // (24 * 60)
    return f"{d} day" + ("s" if d != 1 else "")


def _cfr_display(ratio: float | None) -> str | None:
    if ratio is None:
        return None
    return f"{ratio * 100:.0f}%"


def _trend_for_values(cur: float | None, prev: float | None) -> tuple[Trend | None, float | None]:
    if cur is None or prev is None:
        return None, None
    if prev == 0:
        if cur == 0:
            return Trend.STABLE, 0.0
        return Trend.UP, 100.0
    pct = (cur - prev) / abs(prev) * 100.0
    if abs(pct) < 0.05:
        return Trend.STABLE, round(pct, 1)
    return (Trend.UP if pct > 0 else Trend.DOWN), round(pct, 1)


def _level_for_row(
    *,
    dep: float | None,
    lead: int | None,
    cfr: float | None,
    mttr_alpha: int | None,
) -> PerformanceLevels:
    overall = classify_performance_level(
        deployment_freq_per_week=dep,
        lead_time_minutes=lead,
        change_failure_rate=cfr,
        mttr_minutes=mttr_alpha,
    )
    ov = PerformanceLevel(overall) if overall else None
    d_level = PerformanceLevel(_deployment_level_only(dep)) if dep is not None else None
    l_level = PerformanceLevel(_lead_level_only(lead)) if lead is not None else None
    c_level = PerformanceLevel(_cfr_level_only(cfr)) if cfr is not None else None
    m_level = PerformanceLevel(_mttr_level_only(mttr_alpha)) if mttr_alpha is not None else None
    return PerformanceLevels(
        overall=ov,
        deployment_frequency=d_level,
        lead_time=l_level,
        change_failure_rate=c_level,
        mttr=m_level,
    )


def _deployment_level_only(value: float) -> str:
    if value > 7:
        return "ELITE"
    if value >= 1:
        return "HIGH"
    if value >= (1 / 4):
        return "MEDIUM"
    return "LOW"


def _lead_level_only(value_minutes: int) -> str:
    if value_minutes < 60:
        return "ELITE"
    if value_minutes < 7 * 24 * 60:
        return "HIGH"
    if value_minutes < 30 * 24 * 60:
        return "MEDIUM"
    return "LOW"


def _cfr_level_only(value: float) -> str:
    if value < 0.05:
        return "ELITE"
    if value <= 0.10:
        return "HIGH"
    if value <= 0.15:
        return "MEDIUM"
    return "LOW"


def _mttr_level_only(value_minutes: int) -> str:
    if value_minutes < 60:
        return "ELITE"
    if value_minutes < 24 * 60:
        return "HIGH"
    if value_minutes <= 7 * 24 * 60:
        return "MEDIUM"
    return "LOW"


@dataclass(frozen=True)
class _Window:
    period_start: date
    period_end: date


def _latest_window(
    db: Session,
    *,
    period_type: str,
    repository_id: int | None,
) -> _Window | None:
    q = select(func.max(MetricSnapshot.period_end)).where(MetricSnapshot.period_type == period_type)
    if repository_id is not None:
        q = q.where(MetricSnapshot.repository_id == repository_id)
    max_end = db.scalar(q)
    if max_end is None:
        return None
    q2 = select(MetricSnapshot.period_start).where(
        MetricSnapshot.period_type == period_type,
        MetricSnapshot.period_end == max_end,
    )
    if repository_id is not None:
        q2 = q2.where(MetricSnapshot.repository_id == repository_id)
    start = db.scalar(q2.limit(1))
    if start is None:
        return None
    return _Window(period_start=start, period_end=max_end)


def _previous_window(window: _Window, period_type: str) -> _Window:
    if period_type == "WEEK":
        return _Window(
            period_start=window.period_start - timedelta(days=7),
            period_end=window.period_end - timedelta(days=7),
        )
    if period_type == "MONTH":
        y, m = window.period_start.year, window.period_start.month
        if m == 1:
            prev_start = date(y - 1, 12, 1)
        else:
            prev_start = date(y, m - 1, 1)
        # approximate month end: day before next month start
        if prev_start.month == 12:
            next_m = date(prev_start.year + 1, 1, 1)
        else:
            next_m = date(prev_start.year, prev_start.month + 1, 1)
        prev_end = next_m - timedelta(days=1)
        return _Window(period_start=prev_start, period_end=prev_end)
    # QUARTER
    qm = ((window.period_start.month - 1) // 3) * 3 + 1
    if qm == 1:
        prev_q_start = date(window.period_start.year - 1, 10, 1)
    else:
        prev_q_start = date(window.period_start.year, qm - 3, 1)
    # end of prev quarter: day before current quarter start
    prev_end = window.period_start - timedelta(days=1)
    return _Window(period_start=prev_q_start, period_end=prev_end)


def _load_snapshots_for_window(
    db: Session,
    *,
    period_type: str,
    window: _Window,
    repository_id: int | None,
) -> list[MetricSnapshot]:
    q = select(MetricSnapshot).where(
        MetricSnapshot.period_type == period_type,
        MetricSnapshot.period_start == window.period_start,
        MetricSnapshot.period_end == window.period_end,
        MetricSnapshot.repository_id.isnot(None),
    )
    if repository_id is not None:
        q = q.where(MetricSnapshot.repository_id == repository_id)
    return list(db.execute(q).scalars().all())


def _aggregate_rows(rows: list[MetricSnapshot]) -> dict[str, float | int | None]:
    dep = _mean_float_from_decimal([r.deployment_freq for r in rows])
    lead = _median_int([r.lead_time_minutes for r in rows])
    rw = _median_int([r.release_wait_median_minutes for r in rows])
    cfr = _mean_float_from_decimal([r.change_failure_rate for r in rows])
    mttr_alpha = _median_int([r.mttr_alpha_minutes for r in rows])
    return {
        "deployment_freq": dep,
        "lead_time_minutes": lead,
        "release_wait_median_minutes": rw,
        "change_failure_rate": cfr,
        "mttr_alpha_minutes": mttr_alpha,
    }


def _max_generated_at(rows: list[MetricSnapshot]) -> datetime:
    times = [r.created_at for r in rows if r.created_at is not None]
    if not times:
        return datetime.now(timezone.utc)
    return max(times)


def build_current_metrics_response(
    db: Session,
    *,
    repository_id: int | None = None,
    period_type: str = "WEEK",
) -> CurrentMetricsResponse:
    window = _latest_window(db, period_type=period_type, repository_id=repository_id)
    if window is None:
        today = datetime.now(timezone.utc).date()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        now = datetime.now(timezone.utc)
        z = MetricValue(value=None, unit="DEPLOYMENTS_PER_WEEK", display_value=None)
        m = MetricValue(value=None, unit="MINUTES", display_value=None)
        r = MetricValue(value=None, unit="RATIO", display_value=None)
        return CurrentMetricsResponse(
            deployment_frequency=z,
            lead_time=m,
            change_failure_rate=r,
            mttr=m,
            overall_performance_level=None,
            period_start=monday,
            period_end=sunday,
            repository_count=0,
            generated_at=now,
            mttr_alpha=None,
            release_wait_time=None,
        )

    rows = _load_snapshots_for_window(
        db,
        period_type=period_type,
        window=window,
        repository_id=repository_id,
    )
    prev_w = _previous_window(window, period_type)
    prev_rows = _load_snapshots_for_window(
        db, period_type=period_type, window=prev_w, repository_id=repository_id
    )

    cur = _aggregate_rows(rows)
    prev = _aggregate_rows(prev_rows)

    dep = cur["deployment_freq"]
    dep_p = prev["deployment_freq"]
    lead = cur["lead_time_minutes"]
    lead_p = prev["lead_time_minutes"]
    cfr = cur["change_failure_rate"]
    cfr_p = prev["change_failure_rate"]
    mttr_a = cur["mttr_alpha_minutes"]
    mttr_p = prev["mttr_alpha_minutes"]
    rw = cur["release_wait_median_minutes"]
    rw_p = prev["release_wait_median_minutes"]

    t_dep, p_dep = _trend_for_values(dep, dep_p)
    t_lead, p_lead = _trend_for_values(
        float(lead) if lead is not None else None,
        float(lead_p) if lead_p is not None else None,
    )
    t_cfr, p_cfr = _trend_for_values(cfr, cfr_p)
    t_mttr, p_mttr = _trend_for_values(
        float(mttr_a) if mttr_a is not None else None,
        float(mttr_p) if mttr_p is not None else None,
    )
    t_rw, p_rw = _trend_for_values(
        float(rw) if rw is not None else None,
        float(rw_p) if rw_p is not None else None,
    )

    overall_raw = classify_performance_level(
        deployment_freq_per_week=dep,
        lead_time_minutes=lead,
        change_failure_rate=cfr,
        mttr_minutes=mttr_a,
    )
    overall_pl = PerformanceLevel(overall_raw) if overall_raw else None

    dep_level = (
        PerformanceLevel(_deployment_level_only(dep))
        if dep is not None
        else None
    )
    lead_level = (
        PerformanceLevel(_lead_level_only(lead))
        if lead is not None
        else None
    )
    cfr_level = (
        PerformanceLevel(_cfr_level_only(cfr))
        if cfr is not None
        else None
    )
    mttr_level = (
        PerformanceLevel(_mttr_level_only(mttr_a))
        if mttr_a is not None
        else None
    )

    repo_count = len({r.repository_id for r in rows if r.repository_id is not None})
    if repository_id is not None:
        repo_count = 1 if rows else 0

    gen_at = _max_generated_at(rows)

    return CurrentMetricsResponse(
        deployment_frequency=MetricValue(
            value=dep,
            unit="DEPLOYMENTS_PER_WEEK",
            display_value=f"{dep:.2f}/week" if dep is not None else None,
            trend=t_dep,
            trend_percentage=p_dep,
            performance_level=dep_level,
        ),
        lead_time=MetricValue(
            value=float(lead) if lead is not None else None,
            unit="MINUTES",
            display_value=_minutes_display(lead),
            trend=t_lead,
            trend_percentage=p_lead,
            performance_level=lead_level,
        ),
        change_failure_rate=MetricValue(
            value=cfr,
            unit="RATIO",
            display_value=_cfr_display(cfr),
            trend=t_cfr,
            trend_percentage=p_cfr,
            performance_level=cfr_level,
        ),
        mttr=MetricValue(
            value=float(mttr_a) if mttr_a is not None else None,
            unit="MINUTES",
            display_value=_minutes_display(mttr_a),
            trend=t_mttr,
            trend_percentage=p_mttr,
            performance_level=mttr_level,
        ),
        overall_performance_level=overall_pl,
        period_start=window.period_start,
        period_end=window.period_end,
        repository_count=repo_count,
        generated_at=gen_at,
        mttr_alpha=MetricValue(
            value=float(mttr_a) if mttr_a is not None else None,
            unit="MINUTES",
            display_value=_minutes_display(mttr_a),
            trend=t_mttr,
            trend_percentage=p_mttr,
            performance_level=mttr_level,
        ),
        release_wait_time=MetricValue(
            value=float(rw) if rw is not None else None,
            unit="MINUTES",
            display_value=_minutes_display(rw),
            trend=t_rw,
            trend_percentage=p_rw,
            performance_level=(
                PerformanceLevel(_lead_level_only(rw))
                if rw is not None
                else None
            ),
        ),
    )


def build_history_response(
    db: Session,
    *,
    period_type: PeriodType,
    from_date: date,
    to_date: date,
    repository_id: int | None,
    page: int,
    size: int,
) -> HistoryResponse:
    size = max(1, min(size, 100))
    page = max(0, page)

    q = (
        select(MetricSnapshot.period_start, MetricSnapshot.period_end)
        .where(
            MetricSnapshot.period_type == period_type.value,
            MetricSnapshot.period_end >= from_date,
            MetricSnapshot.period_start <= to_date,
            MetricSnapshot.repository_id.isnot(None),
        )
        .distinct()
        .order_by(MetricSnapshot.period_start.desc())
    )
    if repository_id is not None:
        q = q.where(MetricSnapshot.repository_id == repository_id)

    all_periods = list(db.execute(q).all())
    total_elements = len(all_periods)
    total_pages = (total_elements + size - 1) // size if total_elements else 0
    slice_ = all_periods[page * size : page * size + size]

    data: list[HistoryDataPoint] = []
    for period_start, period_end in slice_:
        w = _Window(period_start=period_start, period_end=period_end)
        rows = _load_snapshots_for_window(
            db,
            period_type=period_type.value,
            window=w,
            repository_id=repository_id,
        )
        agg = _aggregate_rows(rows)
        dep = agg["deployment_freq"]
        lead = agg["lead_time_minutes"]
        cfr = agg["change_failure_rate"]
        mttr_alpha = agg["mttr_alpha_minutes"]
        rw = agg["release_wait_median_minutes"]
        levels = _level_for_row(
            dep=dep,
            lead=lead,
            cfr=cfr,
            mttr_alpha=mttr_alpha,
        )
        data.append(
            HistoryDataPoint(
                period_start=period_start,
                period_end=period_end,
                deployment_frequency=dep,
                lead_time_minutes=lead,
                change_failure_rate=cfr,
                mttr_minutes=mttr_alpha,
                mttr_alpha_minutes=mttr_alpha,
                release_wait_median_minutes=rw,
                performance_level=levels,
            )
        )

    return HistoryResponse(
        period_type=period_type,
        from_date=from_date,
        to_date=to_date,
        repository_id=repository_id,
        data=data,
        pagination=Pagination(
            page=page,
            size=size,
            total_elements=total_elements,
            total_pages=total_pages,
            has_next=(page + 1) * size < total_elements,
            has_previous=page > 0,
        ),
    )

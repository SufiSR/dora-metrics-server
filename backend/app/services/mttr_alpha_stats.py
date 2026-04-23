from __future__ import annotations

import math
from dataclasses import dataclass

# Fixed histogram bins (minutes, upper exclusive except last bucket is unbounded).
# Chosen for a log-like spread from sub-hour to multi-week MTTR.
_MTTR_ALPHA_HISTOGRAM_BINS: tuple[tuple[int, int | None, str], ...] = (
    (0, 60, "≤1h"),
    (60, 240, "1–4h"),
    (240, 1440, "4–24h"),
    (1440, 10080, "1–7d"),
    (10080, 43200, "1–4w"),
    (43200, None, ">4w"),
)


def median_from_sorted(sorted_vals: list[int]) -> int | None:
    """Match ``median_mttr_alpha_minutes`` even-length behaviour (midpoint, rounded int)."""
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return int(round((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0))


def percentile_linear_minutes_sorted(sorted_vals: list[int], q: float) -> float | None:
    """One-dimensional linear interpolation between closest ranks (Type 7, same as ``numpy`` default).

    ``q`` is 0..100. Returns None if there are no values.
    """
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    qf = min(100.0, max(0.0, q)) / 100.0
    n = len(sorted_vals)
    pos = (n - 1) * qf
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_vals[lo])
    w = pos - lo
    return (1.0 - w) * float(sorted_vals[lo]) + w * float(sorted_vals[hi])


@dataclass(frozen=True)
class MttrAlphaPercentiles:
    min_minutes: int | None
    p75_minutes: int | None
    p90_minutes: int | None
    p95_minutes: int | None
    max_minutes: int | None


def percentiles_for_mttr_minutes(sorted_vals: list[int]) -> MttrAlphaPercentiles:
    if not sorted_vals:
        return MttrAlphaPercentiles(
            min_minutes=None,
            p75_minutes=None,
            p90_minutes=None,
            p95_minutes=None,
            max_minutes=None,
        )
    p75 = percentile_linear_minutes_sorted(sorted_vals, 75.0)
    p90 = percentile_linear_minutes_sorted(sorted_vals, 90.0)
    p95 = percentile_linear_minutes_sorted(sorted_vals, 95.0)
    mn = int(sorted_vals[0])
    mx = int(sorted_vals[-1])
    return MttrAlphaPercentiles(
        min_minutes=mn,
        p75_minutes=None if p75 is None else int(round(p75)),
        p90_minutes=None if p90 is None else int(round(p90)),
        p95_minutes=None if p95 is None else int(round(p95)),
        max_minutes=mx,
    )


@dataclass(frozen=True)
class MttrAlphaHistogramBinOut:
    label: str
    start_minutes: int
    end_minutes: int | None
    count: int


def build_mttr_alpha_histogram(values: list[int]) -> list[MttrAlphaHistogramBinOut]:
    """Server-side fixed bins over ``mttr_alpha_minutes`` (same population as summary)."""
    counts = [0] * len(_MTTR_ALPHA_HISTOGRAM_BINS)
    for v in values:
        for i, (lo, hi, _) in enumerate(_MTTR_ALPHA_HISTOGRAM_BINS):
            if hi is None:
                if v >= lo:
                    counts[i] += 1
                break
            if lo <= v < hi:
                counts[i] += 1
                break
    out: list[MttrAlphaHistogramBinOut] = []
    for (lo, hi, label), c in zip(_MTTR_ALPHA_HISTOGRAM_BINS, counts, strict=True):
        out.append(
            MttrAlphaHistogramBinOut(
                label=label, start_minutes=lo, end_minutes=hi, count=c
            )
        )
    return out

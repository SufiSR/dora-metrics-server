"""Unit tests for mttr_alpha_stats pure helpers."""

from __future__ import annotations

from app.services.mttr_alpha_stats import (
    build_mttr_alpha_histogram,
    median_from_sorted,
    percentiles_for_mttr_minutes,
    percentile_linear_minutes_sorted,
)


def test_median_from_sorted_even_count() -> None:
    assert median_from_sorted([1, 2, 3, 4]) == int(round((2 + 3) / 2.0))  # 2
    assert median_from_sorted([10, 20]) == 15


def test_median_from_sorted_empty() -> None:
    assert median_from_sorted([]) is None


def test_percentile_linear_empty() -> None:
    assert percentile_linear_minutes_sorted([], 50.0) is None


def test_percentile_linear_single_value_and_lo_equals_hi() -> None:
    assert percentile_linear_minutes_sorted([42], 50.0) == 42.0
    v = percentile_linear_minutes_sorted([1, 2, 3, 4, 5], 100.0)
    assert v == 5.0


def test_percentiles_for_mttr_minutes_empty() -> None:
    p = percentiles_for_mttr_minutes([])
    assert p.min_minutes is None and p.max_minutes is None


def test_build_mttr_alpha_histogram_last_bin_unbounded() -> None:
    bins = build_mttr_alpha_histogram([50000])
    assert any(b.label == ">4w" and b.count == 1 for b in bins)

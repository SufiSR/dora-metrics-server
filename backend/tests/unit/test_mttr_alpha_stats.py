from __future__ import annotations

import pytest

from app.services.mttr_alpha_stats import (
    build_mttr_alpha_histogram,
    median_from_sorted,
    percentile_linear_minutes_sorted,
    percentiles_for_mttr_minutes,
)


def test_median_from_sorted_odd_even() -> None:
    assert median_from_sorted([1, 2, 3]) == 2
    assert median_from_sorted([10, 20, 30, 40]) == 25


def test_percentile_linear_matches_two_point_case() -> None:
    xs = [120, 300]
    assert pytest.approx(percentile_linear_minutes_sorted(xs, 75.0), rel=1e-9) == 255.0
    assert pytest.approx(percentile_linear_minutes_sorted(xs, 90.0), rel=1e-9) == 282.0


def test_percentiles_for_mttr_minutes_empty() -> None:
    p = percentiles_for_mttr_minutes([])
    assert p.min_minutes is None
    assert p.p75_minutes is None


def test_histogram_bins() -> None:
    h = build_mttr_alpha_histogram([30, 90, 300, 2000, 50000])
    labels = [b.label for b in h]
    assert "≤1h" in labels
    counts = {b.label: b.count for b in h}
    assert counts["≤1h"] == 1
    assert counts["1–4h"] == 1
    assert counts["4–24h"] == 1
    assert counts["1–7d"] == 1
    assert counts[">4w"] == 1

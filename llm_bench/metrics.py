from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Iterable


@dataclass
class StatSummary:
    count: int
    mean: float | None
    p50: float | None
    p90: float | None
    p99: float | None
    std: float | None
    min: float | None
    max: float | None


def _percentile(values: list[float], p: float) -> float:
    if not values:
        raise ValueError("empty values")
    if len(values) == 1:
        return values[0]
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def summarize(values: Iterable[float | None]) -> StatSummary:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return StatSummary(0, None, None, None, None, None, None, None)
    return StatSummary(
        count=len(nums),
        mean=statistics.mean(nums),
        p50=_percentile(nums, 0.5),
        p90=_percentile(nums, 0.9),
        p99=_percentile(nums, 0.99),
        std=statistics.pstdev(nums) if len(nums) > 1 else 0.0,
        min=min(nums),
        max=max(nums),
    )


def format_stat(value: float | None, *, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}{suffix}"

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
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


@dataclass
class DecodeMetrics:
    tps_steady: float | None
    tps_e2e: float | None
    tpot_ms: float | None
    ttft_corrected_ms: float | None
    decode_est_ms: float | None
    buffered: bool
    reliable: bool
    n_chunks: int
    n_core: int


@dataclass
class LoadSLOConfig:
    ttft_ms: float | None = None
    tpot_ms: float | None = None


@dataclass
class LoadSummary:
    request_rate: float
    window_s: float
    achieved_rate: float
    output_throughput: float
    total_throughput: float
    goodput: float
    ttft: StatSummary
    tpot: StatSummary
    tps: StatSummary  # per-request TPS derived from tpot (1000/tpot_ms)
    total_requests: int
    slo_ok_count: int
    by_domain: dict[str, dict[str, float]] = field(default_factory=dict)


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


def _trim_core_bounds(
    n: int,
    intervals: list[float],
    *,
    burst_factor: float,
    trim_head_ratio: float,
    trim_tail_ratio: float,
) -> tuple[int, int]:
    """Return inclusive chunk index bounds [lo, hi] for the steady core window."""
    if n < 2:
        return 0, max(0, n - 1)

    med = statistics.median(intervals)
    threshold = med * burst_factor

    lo_burst = 0
    while lo_burst < len(intervals) and intervals[lo_burst] < threshold:
        lo_burst += 1

    hi_burst = n - 1
    while hi_burst > lo_burst + 1 and intervals[hi_burst - 1] < threshold:
        hi_burst -= 1

    lo_ratio = math.ceil(n * trim_head_ratio)
    tail_trim = math.ceil(n * trim_tail_ratio)
    hi_ratio = max(lo_ratio + 1, n - 1 - tail_trim)

    lo = max(lo_burst, lo_ratio)
    hi = min(hi_burst, hi_ratio)

    if hi <= lo:
        return 0, n - 1
    return lo, hi


def compute_decode_metrics(
    chunk_times: list[float],
    output_tokens: int,
    ttft_ms: float | None,
    total_latency_ms: float,
    *,
    burst_factor: float = 0.5,
    trim_head_ratio: float = 0.1,
    trim_tail_ratio: float = 0.1,
    min_chunks: int = 4,
    buffered_threshold: float = 0.15,
) -> DecodeMetrics:
    """Compute steady decode TPS and back-correct TTFT from total latency.

    Token count comes from usage (reliable). A burst-detected + ratio-floored
    core window estimates steady token rate; full decode time is scaled from
    that rate, then ttft_corrected = total_latency - decode_est.
    """
    n = len(chunk_times)
    empty = DecodeMetrics(
        None, None, None, None, None, False, False, n, 0
    )
    if output_tokens <= 0 or n == 0:
        return empty
    if output_tokens == 1:
        return DecodeMetrics(
            0.0, 0.0, None, ttft_ms, 0.0, False, False, n, 0
        )
    if n < 2:
        return empty

    span = chunk_times[-1] - chunk_times[0]
    tps_e2e: float | None = None
    if span > 0:
        tps_e2e = (output_tokens - 1) / span

    intervals = [chunk_times[i + 1] - chunk_times[i] for i in range(n - 1)]
    lo, hi = _trim_core_bounds(
        n,
        intervals,
        burst_factor=burst_factor,
        trim_head_ratio=trim_head_ratio,
        trim_tail_ratio=trim_tail_ratio,
    )
    core = chunk_times[lo : hi + 1]
    n_core = len(core)
    core_window = core[-1] - core[0] if n_core >= 2 else 0.0

    tps_steady: float | None = None
    if n_core >= 2 and core_window > 0:
        steady_tokens = output_tokens * (n_core - 1) / (n - 1)
        tps_steady = steady_tokens / core_window
    elif tps_e2e is not None:
        tps_steady = tps_e2e

    tpot_ms: float | None = None
    decode_est_ms: float | None = None
    ttft_corrected_ms: float | None = None
    if tps_steady is not None and tps_steady > 0:
        tpot_ms = 1000.0 / tps_steady
        decode_est_ms = output_tokens / tps_steady * 1000.0
        ttft_corrected_ms = max(0.0, total_latency_ms - decode_est_ms)

    reliable = (
        output_tokens > 1
        and n_core >= min_chunks
        and core_window > 0
        and ttft_corrected_ms is not None
        and ttft_corrected_ms > 0
    )
    if ttft_corrected_ms is not None and ttft_corrected_ms <= 0:
        reliable = False

    buffered = False
    if (
        ttft_ms is not None
        and ttft_ms > 0
        and ttft_corrected_ms is not None
        and abs(ttft_corrected_ms - ttft_ms) / ttft_ms > buffered_threshold
    ):
        buffered = True

    return DecodeMetrics(
        tps_steady=tps_steady,
        tps_e2e=tps_e2e,
        tpot_ms=tpot_ms,
        ttft_corrected_ms=ttft_corrected_ms,
        decode_est_ms=decode_est_ms,
        buffered=buffered,
        reliable=reliable,
        n_chunks=n,
        n_core=n_core,
    )


def tps_to_tpot_ms(tps: float | None) -> float | None:
    if tps is None or tps <= 0:
        return None
    return 1000.0 / tps


def tpot_ms_to_tps(tpot_ms: float | None) -> float | None:
    if tpot_ms is None or tpot_ms <= 0:
        return None
    return 1000.0 / tpot_ms


def compute_load_tpot_ms(
    total_latency_ms: float,
    ttft_ms: float | None,
    output_tokens: int,
) -> float | None:
    """Coarse per-request TPOT for load tests: (total - ttft) / (tokens - 1)."""
    if output_tokens <= 1 or ttft_ms is None:
        return 0.0 if output_tokens == 1 else None
    decode_ms = total_latency_ms - ttft_ms
    if decode_ms <= 0:
        return None
    return decode_ms / (output_tokens - 1)


def check_slo(
    *,
    ttft_ms: float | None,
    tpot_ms: float | None,
    slo: LoadSLOConfig,
) -> bool:
    if ttft_ms is None or tpot_ms is None:
        return False
    if slo.ttft_ms is not None and ttft_ms > slo.ttft_ms:
        return False
    if slo.tpot_ms is not None and tpot_ms > slo.tpot_ms:
        return False
    return True


def summarize_load_records(
    records: list,
    *,
    request_rate: float,
    window_s: float,
) -> LoadSummary:
    """Aggregate load-test records into system-level metrics."""
    valid = [r for r in records if r.error is None]
    slo_ok = [r for r in valid if r.slo_ok]

    total_out = sum(r.output_tokens for r in valid)
    total_in_out = sum(r.input_tokens + r.output_tokens for r in valid)

    ttft_vals = [r.ttft_ms for r in valid]
    tpot_vals = [r.tpot_ms for r in valid if r.tpot_ms is not None]
    tps_vals = [tpot_ms_to_tps(t) for t in tpot_vals]

    by_domain: dict[str, dict[str, float]] = {}
    domain_groups: dict[tuple[str, str], list] = {}
    for r in valid:
        key = (r.domain, r.output_style)
        domain_groups.setdefault(key, []).append(r)

    for (domain, style), group in domain_groups.items():
        out_tok = sum(g.output_tokens for g in group)
        tpot_list = [g.tpot_ms for g in group if g.tpot_ms is not None]
        tps_list = [tpot_ms_to_tps(t) for t in tpot_list if t is not None]
        label = f"{domain}/{style}"
        by_domain[label] = {
            "output_throughput": out_tok / window_s if window_s > 0 else 0.0,
            "request_count": len(group),
            "tpot_p50": _percentile(tpot_list, 0.5) if tpot_list else 0.0,
            "tps_p50": _percentile(tps_list, 0.5) if tps_list else 0.0,
        }

    return LoadSummary(
        request_rate=request_rate,
        window_s=window_s,
        achieved_rate=len(valid) / window_s if window_s > 0 else 0.0,
        output_throughput=total_out / window_s if window_s > 0 else 0.0,
        total_throughput=total_in_out / window_s if window_s > 0 else 0.0,
        goodput=len(slo_ok) / window_s if window_s > 0 else 0.0,
        ttft=summarize(ttft_vals),
        tpot=summarize(tpot_vals),
        tps=summarize(tps_vals),
        total_requests=len(valid),
        slo_ok_count=len(slo_ok),
        by_domain=by_domain,
    )


def format_stat(value: float | None, *, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}{suffix}"


def format_tps(value: float | None) -> str:
    return format_stat(value, digits=2)


def format_tpot(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f} ms/tok"


def format_tpot_value(value: float | None) -> str:
    """TPOT numeric only; put units in the column header."""
    if value is None:
        return "n/a"
    return f"{value:.1f}"

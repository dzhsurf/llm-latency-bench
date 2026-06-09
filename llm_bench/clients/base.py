from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StreamResult:
    ttft_ms: float | None  # observed (raw)
    decode_tps: float | None  # steady-state TPS (primary)
    output_tokens: int
    input_tokens: int
    cached_tokens: int
    total_latency_ms: float
    ttft_corrected_ms: float | None = None
    decode_est_ms: float | None = None
    decode_buffered: bool = False
    decode_tps_e2e: float | None = None
    tpot_ms: float | None = None
    decode_reliable: bool = True
    n_chunks: int = 0
    aborted_after_first_token: bool = False
    raw_usage: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class DecodeCalcConfig:
    burst_factor: float = 0.5
    trim_head_ratio: float = 0.1
    trim_tail_ratio: float = 0.1
    min_chunks: int = 4
    buffered_threshold: float = 0.15


class BaseClient(ABC):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = 600.0,
        decode_calc: DecodeCalcConfig | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.decode_calc = decode_calc or DecodeCalcConfig()

    @abstractmethod
    async def stream_completion(
        self,
        prompt: str,
        *,
        max_tokens: int,
        abort_after_first_token: bool = False,
        system: str | None = None,
    ) -> StreamResult:
        raise NotImplementedError

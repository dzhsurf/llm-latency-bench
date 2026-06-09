from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StreamResult:
    ttft_ms: float | None
    decode_tps: float | None
    output_tokens: int
    input_tokens: int
    cached_tokens: int
    total_latency_ms: float
    aborted_after_first_token: bool = False
    raw_usage: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class BaseClient(ABC):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float = 600.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s

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

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ALL_LENGTHS = [1024, 4096, 8192, 16384, 32768, 65536, 131072]


class EndpointConfig(BaseModel):
    base_url: str
    api_type: Literal["openai", "anthropic"]
    api_key: str = "EMPTY"
    model: str

    @field_validator("base_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


class RunConfig(BaseModel):
    repeats: int = 5
    warmup: int = 1
    decode_max_tokens: int = 512
    ttft_only_max_tokens: int = 1
    request_timeout_s: int = 600
    concurrency_levels: list[int] = Field(default_factory=lambda: [1, 4])
    max_cases_per_length: int | None = None  # None = all cases; useful for smoke runs
    decode_burst_factor: float = 0.5
    decode_trim_head_ratio: float = 0.1
    decode_trim_tail_ratio: float = 0.1
    decode_min_chunks: int = 4
    decode_buffered_threshold: float = 0.15


class DomainMatrixEntry(BaseModel):
    lengths: list[int] | Literal["all"] = "all"

    def resolve_lengths(self, context_lengths: list[int]) -> list[int]:
        if self.lengths == "all":
            return list(context_lengths)
        return list(self.lengths)


class MatrixConfig(BaseModel):
    context_lengths: list[int] = Field(default_factory=lambda: list(ALL_LENGTHS))
    domains: dict[str, DomainMatrixEntry]
    test_prefix_caching: bool = True

    @field_validator("context_lengths")
    @classmethod
    def validate_lengths(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("context_lengths must not be empty")
        return sorted(set(v))


class LoadSLOConfig(BaseModel):
    ttft_ms: float | None = None
    tpot_ms: float | None = None


class LoadConfig(BaseModel):
    enabled: bool = False
    request_rate_sweep: list[float] = Field(default_factory=lambda: [2.0, 8.0])
    duration_s: int = 60
    max_concurrency: int | None = None
    cache_hit_ratio: float = 0.0
    warmup_s: int = 0
    slo: LoadSLOConfig = Field(default_factory=LoadSLOConfig)
    sample_domains: list[str] | None = None
    max_tokens: int | None = None


class OutputConfig(BaseModel):
    dir: str = "results"


class BenchConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    endpoint: EndpointConfig
    run: RunConfig = Field(default_factory=RunConfig)
    matrix: MatrixConfig
    load_test: LoadConfig = Field(default_factory=LoadConfig, alias="load")
    output: OutputConfig = Field(default_factory=OutputConfig)

    @model_validator(mode="after")
    def validate_base_url_for_api_type(self) -> BenchConfig:
        if self.endpoint.api_type == "openai" and not self.endpoint.base_url.endswith("/v1"):
            raise ValueError("OpenAI api_type requires base_url to end with /v1")
        if self.endpoint.api_type == "anthropic" and self.endpoint.base_url.endswith("/v1"):
            raise ValueError("Anthropic api_type requires base_url without /v1 suffix")
        return self

    @classmethod
    def load(cls, path: str | Path) -> BenchConfig:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


def resolve_dataset_root() -> Path:
    return Path(__file__).resolve().parent.parent / "datasets"

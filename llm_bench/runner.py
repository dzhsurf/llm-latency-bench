from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from llm_bench.cache_buster import make_cache_buster
from llm_bench.clients import BaseClient, StreamResult, create_client
from llm_bench.config import BenchConfig
from llm_bench.console_log import BenchConsole
from llm_bench.datasets import DatasetItem, filter_items, load_manifest
from llm_bench.metrics import StatSummary, summarize

SYSTEM_PROMPT = (
    "You are an expert technical assistant. Read the user's materials carefully "
    "and produce a thorough, well-structured, and detailed response."
)


@dataclass
class RunRecord:
    run_id: str
    domain: str
    dataset_id: str
    case_index: int
    output_style: str
    target_tokens: int
    measured_tokens: int
    mode: str
    cache_mode: str | None
    concurrency: int
    repeat_index: int
    max_tokens: int
    ttft_ms: float | None
    decode_tps: float | None
    output_tokens: int
    input_tokens: int
    cached_tokens: int
    total_latency_ms: float
    error: str | None = None


@dataclass
class GroupSummary:
    domain: str
    target_tokens: int
    output_style: str
    mode: str
    cache_mode: str | None
    concurrency: int
    ttft: StatSummary
    decode_tps: StatSummary
    cached_tokens: StatSummary
    records: list[RunRecord] = field(default_factory=list)


def _group_key(record: RunRecord) -> tuple:
    return (
        record.domain,
        record.target_tokens,
        record.output_style,
        record.mode,
        record.cache_mode,
        record.concurrency,
    )


def aggregate_records(records: list[RunRecord]) -> list[GroupSummary]:
    groups: dict[tuple, list[RunRecord]] = {}
    for record in records:
        groups.setdefault(_group_key(record), []).append(record)

    summaries: list[GroupSummary] = []
    for key, group_records in sorted(groups.items()):
        domain, target_tokens, output_style, mode, cache_mode, concurrency = key
        summaries.append(
            GroupSummary(
                domain=domain,
                target_tokens=target_tokens,
                output_style=output_style,
                mode=mode,
                cache_mode=cache_mode,
                concurrency=concurrency,
                ttft=summarize(r.ttft_ms for r in group_records),
                decode_tps=summarize(r.decode_tps for r in group_records),
                cached_tokens=summarize(float(r.cached_tokens) for r in group_records),
                records=group_records,
            )
        )
    return summaries


class BenchmarkRunner:
    def __init__(self, config: BenchConfig, *, verbose: bool = True) -> None:
        self.config = config
        self.log = BenchConsole(enabled=verbose)
        self.client: BaseClient = create_client(
            config.endpoint.api_type,
            config.endpoint.base_url,
            config.endpoint.api_key,
            config.endpoint.model,
            float(config.run.request_timeout_s),
        )
        self.records: list[RunRecord] = []

    def _resolved_domains(self) -> dict[str, list[int]]:
        return {
            name: entry.resolve_lengths(self.config.matrix.context_lengths)
            for name, entry in self.config.matrix.domains.items()
        }

    def _make_record(
        self,
        *,
        item: DatasetItem,
        mode: str,
        cache_mode: str | None,
        concurrency: int,
        repeat_index: int,
        max_tokens: int,
        result: StreamResult,
    ) -> RunRecord:
        return RunRecord(
            run_id=str(uuid.uuid4()),
            domain=item.domain,
            dataset_id=item.id,
            case_index=item.case_index,
            output_style=item.output_style,
            target_tokens=item.target_tokens,
            measured_tokens=item.measured_tokens,
            mode=mode,
            cache_mode=cache_mode,
            concurrency=concurrency,
            repeat_index=repeat_index,
            max_tokens=max_tokens,
            ttft_ms=result.ttft_ms,
            decode_tps=result.decode_tps,
            output_tokens=result.output_tokens,
            input_tokens=result.input_tokens,
            cached_tokens=result.cached_tokens,
            total_latency_ms=result.total_latency_ms,
            error=result.error,
        )

    async def _run_once(
        self,
        prompt: str,
        *,
        max_tokens: int,
        abort_after_first_token: bool,
        system: str | None = None,
    ) -> StreamResult:
        return await self.client.stream_completion(
            prompt,
            max_tokens=max_tokens,
            abort_after_first_token=abort_after_first_token,
            system=system,
        )

    async def _run_logged(
        self,
        prompt: str,
        *,
        label: str,
        cache_mode: str,
        max_tokens: int,
        abort_after_first_token: bool,
        system: str | None = None,
    ) -> StreamResult:
        self.log.request_start(label=label, cache_mode=cache_mode, max_tokens=max_tokens)
        started = time.perf_counter()
        result = await self._run_once(
            prompt,
            max_tokens=max_tokens,
            abort_after_first_token=abort_after_first_token,
            system=system,
        )
        self.log.request_done(
            label=label,
            result=result,
            elapsed_s=time.perf_counter() - started,
        )
        return result

    def _emit_ttft_and_decode(
        self,
        item: DatasetItem,
        result: StreamResult,
        *,
        cache_mode: str,
        concurrency: int,
        repeat_index: int,
    ) -> list[RunRecord]:
        """Derive a TTFT row and a decode row from a single full request."""
        ttft = self._make_record(
            item=item,
            mode="ttft",
            cache_mode=cache_mode,
            concurrency=concurrency,
            repeat_index=repeat_index,
            max_tokens=self.config.run.decode_max_tokens,
            result=result,
        )
        # The TTFT row reports first-token latency only; decode TPS lives on the
        # decode row so the two concerns stay separate in the report.
        ttft.decode_tps = None
        decode = self._make_record(
            item=item,
            mode="decode",
            cache_mode=cache_mode,
            concurrency=concurrency,
            repeat_index=repeat_index,
            max_tokens=self.config.run.decode_max_tokens,
            result=result,
        )
        return [ttft, decode]

    async def _run_repeat_serial(
        self,
        item: DatasetItem,
        *,
        concurrency: int,
        repeat_index: int,
    ) -> list[RunRecord]:
        """One repeat using a unified, non-abort request shape.

        A random cache buster (random bytes plus a time factor) is created per
        repeat and appended to BOTH the system prompt and the user prompt, so the
        pair is unique across repeats but identical within a repeat. Both calls
        run the FULL decode (never abort): aborting after the first token would
        prevent reading end-of-stream usage, so the prefix-cache hit rate
        (cached_tokens) could not be confirmed on the warm call.

          1. cold: first time this buster is seen -> prefix-cache MISS. Yields
             TTFT miss, cached_tokens (expected 0), decode; also populates cache.
          2. warm: identical system+user prompt -> prefix-cache HIT. Yields TTFT
             hit, cached_tokens (> 0, confirming the hit), and decode.

        Because both calls share the exact same request shape and max_tokens, the
        TTFT miss vs hit comparison is apples-to-apples at every context length.
        Decode is reported for both; cache only affects prefill, so the hit decode
        is the primary decode-speed metric.
        """
        caching = self.config.matrix.test_prefix_caching
        buster = make_cache_buster(fixed=False)
        system_prompt = buster + SYSTEM_PROMPT
        user_prompt = buster + item.prompt

        decode_max = self.config.run.decode_max_tokens

        if not caching:
            result = await self._run_logged(
                user_prompt,
                label="request",
                cache_mode="nocache",
                system=system_prompt,
                max_tokens=decode_max,
                abort_after_first_token=False,
            )
            return self._emit_ttft_and_decode(
                item,
                result,
                cache_mode="nocache",
                concurrency=concurrency,
                repeat_index=repeat_index,
            )

        records: list[RunRecord] = []
        cold = await self._run_logged(
            user_prompt,
            label="cold",
            cache_mode="miss",
            system=system_prompt,
            max_tokens=decode_max,
            abort_after_first_token=False,
        )
        records.extend(
            self._emit_ttft_and_decode(
                item,
                cold,
                cache_mode="miss",
                concurrency=concurrency,
                repeat_index=repeat_index,
            )
        )

        warm = await self._run_logged(
            user_prompt,
            label="warm",
            cache_mode="hit",
            system=system_prompt,
            max_tokens=decode_max,
            abort_after_first_token=False,
        )
        records.extend(
            self._emit_ttft_and_decode(
                item,
                warm,
                cache_mode="hit",
                concurrency=concurrency,
                repeat_index=repeat_index,
            )
        )
        return records

    async def _run_concurrent_throughput(
        self,
        item: DatasetItem,
        *,
        concurrency: int,
    ) -> list[RunRecord]:
        async def one() -> RunRecord:
            buster = make_cache_buster(fixed=False)
            result = await self._run_once(
                buster + item.prompt,
                system=buster + SYSTEM_PROMPT,
                max_tokens=min(512, self.config.run.decode_max_tokens),
                abort_after_first_token=False,
            )
            return self._make_record(
                item=item,
                mode="throughput",
                cache_mode="nocache",
                concurrency=concurrency,
                repeat_index=0,
                max_tokens=min(512, self.config.run.decode_max_tokens),
                result=result,
            )

        return await asyncio.gather(*[one() for _ in range(concurrency)])

    async def run_item_serial(self, item: DatasetItem, concurrency: int) -> None:
        for w in range(self.config.run.warmup):
            self.log.warmup(round_index=w, total=self.config.run.warmup)
            buster = make_cache_buster(fixed=False)
            await self._run_once(
                buster + item.prompt,
                system=buster + SYSTEM_PROMPT,
                max_tokens=1,
                abort_after_first_token=True,
            )

        for repeat in range(self.config.run.repeats):
            self.log.repeat_start(repeat_index=repeat, repeats=self.config.run.repeats)
            self.records.extend(
                await self._run_repeat_serial(
                    item, concurrency=concurrency, repeat_index=repeat
                )
            )

    async def run_item_throughput(self, item: DatasetItem, concurrency: int) -> None:
        if concurrency <= 1:
            return
        self.log.throughput_start(concurrency=concurrency)
        self.records.extend(await self._run_concurrent_throughput(item, concurrency))

    async def run(self, *, domain_filter: str | None = None, length_filter: int | None = None) -> list[RunRecord]:
        items = filter_items(load_manifest(), domains=self._resolved_domains())
        if domain_filter:
            items = [i for i in items if i.domain == domain_filter]
        if length_filter is not None:
            items = [i for i in items if i.target_tokens == length_filter]

        max_cases = self.config.run.max_cases_per_length
        if max_cases is not None:
            seen: dict[tuple[str, int], int] = {}
            limited: list[DatasetItem] = []
            for item in sorted(items, key=lambda i: (i.domain, i.target_tokens, i.case_index)):
                key = (item.domain, item.target_tokens)
                if seen.get(key, 0) >= max_cases:
                    continue
                seen[key] = seen.get(key, 0) + 1
                limited.append(item)
            items = limited

        self.log.banner(
            self.config,
            item_count=len(items),
            domain_filter=domain_filter,
            length_filter=length_filter,
        )
        if not items:
            self.log.no_items()
            self.elapsed_s = 0.0
            return self.records

        started = time.perf_counter()
        total = len(items)
        for index, item in enumerate(items, start=1):
            for concurrency in self.config.run.concurrency_levels:
                self.log.item_start(
                    index=index,
                    total=total,
                    item=item,
                    concurrency=concurrency,
                )
                if concurrency == 1:
                    await self.run_item_serial(item, concurrency)
                else:
                    await self.run_item_throughput(item, concurrency)

        elapsed = time.perf_counter() - started
        self.elapsed_s = elapsed
        self.log.done(record_count=len(self.records), elapsed_s=elapsed)
        return self.records

    def summaries(self) -> list[GroupSummary]:
        return aggregate_records(self.records)

    def to_json(self) -> dict[str, Any]:
        return {
            "config": {
                "endpoint": self.config.endpoint.model_dump(),
                "run": self.config.run.model_dump(),
                "matrix": self.config.matrix.model_dump(),
            },
            "elapsed_s": getattr(self, "elapsed_s", None),
            "records": [asdict(r) for r in self.records],
            "summaries": [
                {
                    "domain": s.domain,
                    "target_tokens": s.target_tokens,
                    "output_style": s.output_style,
                    "mode": s.mode,
                    "cache_mode": s.cache_mode,
                    "concurrency": s.concurrency,
                    "ttft": asdict(s.ttft),
                    "decode_tps": asdict(s.decode_tps),
                    "cached_tokens": asdict(s.cached_tokens),
                }
                for s in self.summaries()
            ],
        }

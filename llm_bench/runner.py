from __future__ import annotations

import asyncio
import math
import random
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from llm_bench.cache_buster import make_cache_buster
from llm_bench.clients import BaseClient, DecodeCalcConfig, StreamResult, create_client
from llm_bench.config import BenchConfig
from llm_bench.console_log import BenchConsole
from llm_bench.datasets import DatasetItem, filter_items, load_manifest
from llm_bench.session import SessionStore, plan_units, sort_items
from llm_bench.metrics import (
    LoadSLOConfig,
    LoadSummary,
    StatSummary,
    check_slo,
    compute_load_tpot_ms,
    summarize,
    summarize_load_records,
)

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
    ttft_corrected_ms: float | None = None
    decode_est_ms: float | None = None
    decode_buffered: bool = False
    decode_tps_e2e: float | None = None
    tpot_ms: float | None = None
    decode_reliable: bool = True
    error: str | None = None


@dataclass
class LoadRecord:
    domain: str
    output_style: str
    target_tokens: int
    cache_mode: str
    request_rate: float
    ttft_ms: float | None
    tpot_ms: float | None
    output_tokens: int
    input_tokens: int
    cached_tokens: int
    total_latency_ms: float
    start_offset_s: float
    slo_ok: bool
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
    ttft_corrected: StatSummary
    decode_tps: StatSummary
    decode_tps_all: StatSummary
    tpot: StatSummary
    cached_tokens: StatSummary
    reliable_count: int = 0
    buffered_count: int = 0
    total_count: int = 0
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
        reliable = [r for r in group_records if r.decode_reliable and r.decode_tps is not None]
        decode_all = [r for r in group_records if r.decode_tps is not None]
        tpot_reliable = [r for r in reliable if r.tpot_ms is not None]

        ttft_corr_reliable = [
            r for r in reliable if r.ttft_corrected_ms is not None
        ]

        summaries.append(
            GroupSummary(
                domain=domain,
                target_tokens=target_tokens,
                output_style=output_style,
                mode=mode,
                cache_mode=cache_mode,
                concurrency=concurrency,
                ttft=summarize(r.ttft_ms for r in group_records),
                ttft_corrected=summarize(
                    r.ttft_corrected_ms for r in ttft_corr_reliable or group_records
                ),
                decode_tps=summarize(r.decode_tps for r in reliable),
                decode_tps_all=summarize(r.decode_tps_e2e for r in decode_all),
                tpot=summarize(r.tpot_ms for r in tpot_reliable),
                cached_tokens=summarize(float(r.cached_tokens) for r in group_records),
                reliable_count=len(reliable),
                buffered_count=sum(1 for r in group_records if r.decode_buffered),
                total_count=len(group_records),
                records=group_records,
            )
        )
    return summaries


def items_by_id(items: list[DatasetItem]) -> dict[str, DatasetItem]:
    return {item.id: item for item in items}


class BenchmarkRunner:
    def __init__(self, config: BenchConfig, *, verbose: bool = True) -> None:
        self.config = config
        self.log = BenchConsole(enabled=verbose)
        decode_calc = DecodeCalcConfig(
            burst_factor=config.run.decode_burst_factor,
            trim_head_ratio=config.run.decode_trim_head_ratio,
            trim_tail_ratio=config.run.decode_trim_tail_ratio,
            min_chunks=config.run.decode_min_chunks,
            buffered_threshold=config.run.decode_buffered_threshold,
        )
        self.client: BaseClient = create_client(
            config.endpoint.api_type,
            config.endpoint.base_url,
            config.endpoint.api_key,
            config.endpoint.model,
            float(config.run.request_timeout_s),
            decode_calc,
        )
        self.records: list[RunRecord] = []
        self.load_records: list[LoadRecord] = []
        self.load_summaries: list[LoadSummary] = []
        self.session: SessionStore | None = None
        self.elapsed_s: float = 0.0

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
            ttft_corrected_ms=result.ttft_corrected_ms,
            decode_est_ms=result.decode_est_ms,
            decode_buffered=result.decode_buffered,
            decode_tps=result.decode_tps,
            decode_tps_e2e=result.decode_tps_e2e,
            tpot_ms=result.tpot_ms,
            decode_reliable=result.decode_reliable,
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
        ttft.decode_tps = None
        ttft.decode_tps_e2e = None
        ttft.tpot_ms = None
        ttft.decode_est_ms = None
        ttft.decode_buffered = False
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

    def _filter_items_for_run(
        self,
        *,
        domain_filter: str | None,
        length_filter: int | None,
    ) -> list[DatasetItem]:
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
        return sort_items(items)

    def _filter_items_for_load(self) -> list[DatasetItem]:
        items = self._filter_items_for_run(domain_filter=None, length_filter=None)
        sample_domains = self.config.load_test.sample_domains
        if sample_domains:
            items = [i for i in items if i.domain in sample_domains]
        return items

    async def _run_load_point(
        self,
        rate: float,
        items: list[DatasetItem],
    ) -> tuple[list[LoadRecord], LoadSummary]:
        load_cfg = self.config.load_test
        duration_s = load_cfg.duration_s
        max_tokens = load_cfg.max_tokens or self.config.run.decode_max_tokens
        slo = LoadSLOConfig(
            ttft_ms=load_cfg.slo.ttft_ms,
            tpot_ms=load_cfg.slo.tpot_ms,
        )

        sent_pool: list[tuple[str, str, DatasetItem]] = []
        records: list[LoadRecord] = []
        in_flight: set[asyncio.Task[LoadRecord]] = set()
        sem = (
            asyncio.Semaphore(load_cfg.max_concurrency)
            if load_cfg.max_concurrency
            else None
        )

        start_wall = time.perf_counter()
        stop_at = start_wall + duration_s
        last_progress = start_wall

        async def execute_one(
            system: str,
            user: str,
            item: DatasetItem,
            cache_mode: str,
            offset_s: float,
        ) -> LoadRecord:
            if sem:
                async with sem:
                    result = await self._run_once(
                        user,
                        system=system,
                        max_tokens=max_tokens,
                        abort_after_first_token=False,
                    )
            else:
                result = await self._run_once(
                    user,
                    system=system,
                    max_tokens=max_tokens,
                    abort_after_first_token=False,
                )

            tpot = compute_load_tpot_ms(
                result.total_latency_ms,
                result.ttft_ms,
                result.output_tokens,
            )
            slo_ok = (
                check_slo(ttft_ms=result.ttft_ms, tpot_ms=tpot, slo=slo)
                if result.error is None
                else False
            )
            return LoadRecord(
                domain=item.domain,
                output_style=item.output_style,
                target_tokens=item.target_tokens,
                cache_mode=cache_mode,
                request_rate=rate,
                ttft_ms=result.ttft_ms,
                tpot_ms=tpot,
                output_tokens=result.output_tokens,
                input_tokens=result.input_tokens,
                cached_tokens=result.cached_tokens,
                total_latency_ms=result.total_latency_ms,
                start_offset_s=offset_s,
                slo_ok=slo_ok,
                error=result.error,
            )

        def pick_prompt() -> tuple[str, str, DatasetItem, str]:
            hit = sent_pool and random.random() < load_cfg.cache_hit_ratio
            if hit:
                system, user, item = random.choice(sent_pool)
                return system, user, item, "hit"
            item = random.choice(items)
            buster = make_cache_buster(fixed=False)
            system = buster + SYSTEM_PROMPT
            user = buster + item.prompt
            sent_pool.append((system, user, item))
            return system, user, item, "miss"

        def _on_task_done(task: asyncio.Task[LoadRecord]) -> None:
            in_flight.discard(task)
            try:
                records.append(task.result())
            except Exception as exc:  # noqa: BLE001
                records.append(
                    LoadRecord(
                        domain="",
                        output_style="",
                        target_tokens=0,
                        cache_mode="miss",
                        request_rate=rate,
                        ttft_ms=None,
                        tpot_ms=None,
                        output_tokens=0,
                        input_tokens=0,
                        cached_tokens=0,
                        total_latency_ms=0.0,
                        start_offset_s=0.0,
                        slo_ok=False,
                        error=str(exc),
                    )
                )

        self.log.load_point_start(rate=rate, duration_s=duration_s)

        while time.perf_counter() < stop_at:
            offset_s = time.perf_counter() - start_wall
            system, user, item, cache_mode = pick_prompt()

            task = asyncio.create_task(
                execute_one(system, user, item, cache_mode, offset_s)
            )
            in_flight.add(task)
            task.add_done_callback(_on_task_done)

            now = time.perf_counter()
            if now - last_progress >= 5.0:
                self.log.load_progress(
                    elapsed_s=now - start_wall,
                    duration_s=duration_s,
                    in_flight=len(in_flight),
                    completed=len(records),
                )
                last_progress = now

            if math.isinf(rate):
                await asyncio.sleep(0)
            else:
                interval = random.expovariate(rate)
                await asyncio.sleep(interval)

        if in_flight:
            await asyncio.gather(*in_flight, return_exceptions=True)

        # Filter warmup window
        warmup_s = load_cfg.warmup_s
        filtered = [r for r in records if r.start_offset_s >= warmup_s]
        if not filtered:
            filtered = records

        window_s = duration_s - warmup_s if duration_s > warmup_s else duration_s
        summary = summarize_load_records(filtered, request_rate=rate, window_s=window_s)
        self.log.load_point_done(summary=summary)
        return filtered, summary

    async def run_load(self) -> None:
        items = self._filter_items_for_load()
        if not items:
            self.log.no_items()
            return

        self.log.load_banner(self.config, item_count=len(items))
        for rate in self.config.load_test.request_rate_sweep:
            records, summary = await self._run_load_point(rate, items)
            self.load_records.extend(records)
            self.load_summaries.append(summary)

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

    async def _run_work_unit(
        self,
        item: DatasetItem,
        concurrency: int,
        *,
        progress_index: int,
        progress_total: int,
    ) -> None:
        self.log.item_start(
            index=progress_index,
            total=progress_total,
            item=item,
            concurrency=concurrency,
        )
        records_before = len(self.records)
        unit_started = time.perf_counter()
        if concurrency == 1:
            await self.run_item_serial(item, concurrency)
        else:
            await self.run_item_throughput(item, concurrency)
        elapsed_delta = time.perf_counter() - unit_started

        if self.session is not None:
            new_records = self.records[records_before:]
            self.session.append_unit(item.id, concurrency, new_records, elapsed_delta)
            from llm_bench.report import write_session_report

            write_session_report(self, self.session.path)

    async def run(
        self,
        *,
        session: SessionStore | None = None,
        domain_filter: str | None = None,
        length_filter: int | None = None,
    ) -> list[RunRecord]:
        self.session = session

        if self.config.load_test.enabled:
            await self.run_load()
            self.elapsed_s = 0.0
            return self.records

        if session is not None:
            self.records = session.load_records()
            self.elapsed_s = session.elapsed_s
            lookup = items_by_id(load_manifest())
            work = [
                (lookup[u["dataset_id"]], int(u["concurrency"]))
                for u in session.remaining_units()
                if u["dataset_id"] in lookup
            ]
            progress_total = session.total_units
            self.log.banner(
                self.config,
                item_count=len(work),
                domain_filter=domain_filter,
                length_filter=length_filter,
            )
            if not work:
                self.log.done(record_count=len(self.records), elapsed_s=self.elapsed_s)
                return self.records

            for wi, (item, concurrency) in enumerate(work, start=1):
                await self._run_work_unit(
                    item,
                    concurrency,
                    progress_index=session.completed_count + wi,
                    progress_total=progress_total,
                )

            self.elapsed_s = session.elapsed_s
            self.log.done(record_count=len(self.records), elapsed_s=self.elapsed_s)
            return self.records

        items = self._filter_items_for_run(
            domain_filter=domain_filter,
            length_filter=length_filter,
        )

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
        units = plan_units(items, self.config.run.concurrency_levels)
        total = len(units)
        for unit_index, unit in enumerate(units, start=1):
            item = items_by_id(items)[unit["dataset_id"]]
            await self._run_work_unit(
                item,
                int(unit["concurrency"]),
                progress_index=unit_index,
                progress_total=total,
            )

        self.elapsed_s = time.perf_counter() - started
        self.log.done(record_count=len(self.records), elapsed_s=self.elapsed_s)
        return self.records

    def summaries(self) -> list[GroupSummary]:
        return aggregate_records(self.records)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "config": {
                "endpoint": self.config.endpoint.model_dump(),
                "run": self.config.run.model_dump(),
                "matrix": self.config.matrix.model_dump(),
                "load": self.config.load_test.model_dump(),
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
                    "ttft_observed": asdict(s.ttft),
                    "ttft_corrected": asdict(s.ttft_corrected),
                    "decode_tps": asdict(s.decode_tps),
                    "decode_tps_e2e": asdict(s.decode_tps_all),
                    "tpot": asdict(s.tpot),
                    "cached_tokens": asdict(s.cached_tokens),
                    "reliable_count": s.reliable_count,
                    "buffered_count": s.buffered_count,
                    "total_count": s.total_count,
                }
                for s in self.summaries()
            ],
        }
        if self.load_records:
            payload["load_records"] = [asdict(r) for r in self.load_records]
        if self.load_summaries:
            payload["load_summaries"] = [
                {
                    "request_rate": ls.request_rate,
                    "window_s": ls.window_s,
                    "achieved_rate": ls.achieved_rate,
                    "output_throughput": ls.output_throughput,
                    "total_throughput": ls.total_throughput,
                    "goodput": ls.goodput,
                    "ttft": asdict(ls.ttft),
                    "tpot": asdict(ls.tpot),
                    "tps": asdict(ls.tps),
                    "total_requests": ls.total_requests,
                    "slo_ok_count": ls.slo_ok_count,
                    "by_domain": ls.by_domain,
                }
                for ls in self.load_summaries
            ]
        return payload

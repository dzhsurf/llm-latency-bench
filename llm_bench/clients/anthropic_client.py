from __future__ import annotations

import json
import time
from typing import Any

import httpx

from llm_bench.clients.base import BaseClient, StreamResult
from llm_bench.metrics import compute_decode_metrics


class AnthropicClient(BaseClient):
    async def stream_completion(
        self,
        prompt: str,
        *,
        max_tokens: int,
        abort_after_first_token: bool = False,
        system: str | None = None,
    ) -> StreamResult:
        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        # Anthropic streams usage by default (message_start + message_delta events);
        # no stream_options equivalent is required.
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        start = time.perf_counter()
        first_token_at: float | None = None
        chunk_times: list[float] = []
        output_tokens = 0
        input_tokens = 0
        cached_tokens = 0
        raw_usage: dict[str, Any] = {}
        error: str | None = None
        aborted = False

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        return StreamResult(
                            ttft_ms=None,
                            decode_tps=None,
                            output_tokens=0,
                            input_tokens=0,
                            cached_tokens=0,
                            total_latency_ms=(time.perf_counter() - start) * 1000,
                            error=f"HTTP {resp.status_code}: {body.decode(errors='replace')}",
                        )

                    event_type = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                            continue
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data:
                            continue
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        if event_type == "message_start":
                            message = chunk.get("message") or {}
                            usage = message.get("usage") or {}
                            raw_usage = usage
                            input_tokens = int(usage.get("input_tokens") or 0)
                            cached_tokens = int(usage.get("cache_read_input_tokens") or 0)
                        elif event_type == "content_block_delta":
                            delta = chunk.get("delta") or {}
                            if delta.get("type") == "text_delta" and delta.get("text"):
                                now = time.perf_counter()
                                if first_token_at is None:
                                    first_token_at = now
                                    if abort_after_first_token:
                                        aborted = True
                                        break
                                chunk_times.append(now - start)
                                output_tokens = max(output_tokens, 1)
                        elif event_type == "message_delta":
                            usage = chunk.get("usage") or {}
                            raw_usage = {**raw_usage, **usage}
                            output_tokens = int(usage.get("output_tokens") or output_tokens)
                            cached_tokens = int(
                                usage.get("cache_read_input_tokens") or cached_tokens
                            )

                    if aborted:
                        await resp.aclose()
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

        end = time.perf_counter()
        total_ms = (end - start) * 1000
        ttft_ms = (first_token_at - start) * 1000 if first_token_at else None

        decode_tps: float | None = None
        decode_tps_e2e: float | None = None
        tpot_ms: float | None = None
        ttft_corrected_ms: float | None = None
        decode_est_ms: float | None = None
        decode_buffered = False
        decode_reliable = True
        n_chunks = len(chunk_times)

        if not aborted and chunk_times and output_tokens > 0:
            cfg = self.decode_calc
            metrics = compute_decode_metrics(
                chunk_times,
                output_tokens,
                ttft_ms,
                total_ms,
                burst_factor=cfg.burst_factor,
                trim_head_ratio=cfg.trim_head_ratio,
                trim_tail_ratio=cfg.trim_tail_ratio,
                min_chunks=cfg.min_chunks,
                buffered_threshold=cfg.buffered_threshold,
            )
            decode_tps = metrics.tps_steady
            decode_tps_e2e = metrics.tps_e2e
            tpot_ms = metrics.tpot_ms
            ttft_corrected_ms = metrics.ttft_corrected_ms
            decode_est_ms = metrics.decode_est_ms
            decode_buffered = metrics.buffered
            decode_reliable = metrics.reliable
            n_chunks = metrics.n_chunks

        return StreamResult(
            ttft_ms=ttft_ms,
            ttft_corrected_ms=ttft_corrected_ms,
            decode_est_ms=decode_est_ms,
            decode_buffered=decode_buffered,
            decode_tps=decode_tps,
            decode_tps_e2e=decode_tps_e2e,
            tpot_ms=tpot_ms,
            decode_reliable=decode_reliable,
            n_chunks=n_chunks,
            output_tokens=output_tokens,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            total_latency_ms=total_ms,
            aborted_after_first_token=aborted,
            raw_usage=raw_usage,
            error=error,
        )

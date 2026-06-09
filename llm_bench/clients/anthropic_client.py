from __future__ import annotations

import json
import time
from typing import Any

import httpx

from llm_bench.clients.base import BaseClient, StreamResult


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
        last_token_at: float | None = None
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
                                last_token_at = now
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
        decode_tps = None
        decode_end = last_token_at or end
        if first_token_at and output_tokens > 1 and not aborted:
            decode_seconds = decode_end - first_token_at
            if decode_seconds > 0:
                decode_tps = (output_tokens - 1) / decode_seconds
        elif first_token_at and output_tokens == 1:
            decode_tps = 0.0

        return StreamResult(
            ttft_ms=ttft_ms,
            decode_tps=decode_tps,
            output_tokens=output_tokens,
            input_tokens=input_tokens,
            cached_tokens=cached_tokens,
            total_latency_ms=total_ms,
            aborted_after_first_token=aborted,
            raw_usage=raw_usage,
            error=error,
        )

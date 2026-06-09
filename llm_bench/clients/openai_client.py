from __future__ import annotations

import json
import time
from typing import Any

import httpx

from llm_bench.clients.base import BaseClient, StreamResult


class OpenAIClient(BaseClient):
    async def stream_completion(
        self,
        prompt: str,
        *,
        max_tokens: int,
        abort_after_first_token: bool = False,
        system: str | None = None,
    ) -> StreamResult:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
            # OpenAI-only: ask the server to emit a final chunk with usage stats.
            "stream_options": {"include_usage": True},
        }

        start = time.perf_counter()
        first_token_at: float | None = None
        last_token_at: float | None = None
        streamed_chunks = 0
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

                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        usage = chunk.get("usage")
                        if usage:
                            raw_usage = usage
                            input_tokens = int(usage.get("prompt_tokens") or 0)
                            output_tokens = int(usage.get("completion_tokens") or output_tokens)
                            details = usage.get("prompt_tokens_details") or {}
                            cached_tokens = int(details.get("cached_tokens") or 0)

                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        content = delta.get("content")
                        if content:
                            streamed_chunks += 1
                            now = time.perf_counter()
                            if first_token_at is None:
                                first_token_at = now
                                if abort_after_first_token:
                                    aborted = True
                                    break
                            last_token_at = now

                    if aborted:
                        await resp.aclose()
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

        if output_tokens == 0 and streamed_chunks > 0:
            output_tokens = streamed_chunks

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

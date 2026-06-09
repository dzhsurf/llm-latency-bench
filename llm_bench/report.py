from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from llm_bench.metrics import format_stat
from llm_bench.runner import BenchmarkRunner, GroupSummary


def _cache_ratio(hit: GroupSummary | None, miss: GroupSummary | None) -> str:
    if not hit or not miss or hit.ttft.mean is None or miss.ttft.mean is None or miss.ttft.mean == 0:
        return "n/a"
    ratio = miss.ttft.mean / hit.ttft.mean
    return f"{ratio:.2f}x"


def build_markdown(summaries: list[GroupSummary]) -> str:
    lines = [
        "# LLM API Benchmark Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Latency and Decode",
        "",
    ]

    latency_rows = []
    for s in summaries:
        if s.mode not in {"decode", "ttft"}:
            continue
        latency_rows.append(
            [
                s.domain,
                s.target_tokens,
                s.output_style,
                s.mode,
                s.cache_mode or "-",
                s.concurrency,
                s.ttft.count,
                format_stat(s.ttft.mean, suffix=" ms"),
                format_stat(s.ttft.p50, suffix=" ms"),
                format_stat(s.ttft.p90, suffix=" ms"),
                format_stat(s.decode_tps.mean, suffix=" t/s"),
                format_stat(s.cached_tokens.mean, digits=0),
            ]
        )

    lines.append(
        tabulate(
            latency_rows,
            headers=[
                "domain",
                "target_tokens",
                "output_style",
                "mode",
                "cache",
                "concurrency",
                "n",
                "ttft_mean",
                "ttft_p50",
                "ttft_p90",
                "decode_tps_mean",
                "cached_tokens_mean",
            ],
            tablefmt="github",
        )
    )

    lines.extend(["", "## Prefix Cache TTFT Comparison", ""])
    cache_rows = []
    grouped: dict[tuple[str, int, str, int], dict[str, GroupSummary]] = {}
    for s in summaries:
        if s.mode != "ttft":
            continue
        key = (s.domain, s.target_tokens, s.output_style, s.concurrency)
        grouped.setdefault(key, {})[s.cache_mode or ""] = s

    for (domain, target_tokens, output_style, concurrency), modes in sorted(grouped.items()):
        hit = modes.get("hit")
        miss = modes.get("miss")
        cache_rows.append(
            [
                domain,
                target_tokens,
                output_style,
                concurrency,
                format_stat(miss.ttft.mean if miss else None, suffix=" ms"),
                format_stat(hit.ttft.mean if hit else None, suffix=" ms"),
                _cache_ratio(hit, miss),
                format_stat(hit.cached_tokens.mean if hit else None, digits=0),
                format_stat(miss.cached_tokens.mean if miss else None, digits=0),
            ]
        )

    lines.append(
        tabulate(
            cache_rows,
            headers=[
                "domain",
                "target_tokens",
                "output_style",
                "concurrency",
                "ttft_miss_mean",
                "ttft_hit_mean",
                "speedup",
                "cached_hit_mean",
                "cached_miss_mean",
            ],
            tablefmt="github",
        )
    )
    return "\n".join(lines) + "\n"


def print_console(summaries: list[GroupSummary]) -> None:
    console = Console()
    table = Table(title="Benchmark Summary")
    for col in [
        "domain",
        "tokens",
        "style",
        "mode",
        "cache",
        "ccy",
        "ttft_mean",
        "decode_tps",
        "cached",
    ]:
        table.add_column(col)

    for s in summaries:
        table.add_row(
            s.domain,
            str(s.target_tokens),
            s.output_style,
            s.mode,
            s.cache_mode or "-",
            str(s.concurrency),
            format_stat(s.ttft.mean, suffix="ms"),
            format_stat(s.decode_tps.mean, suffix="/s"),
            format_stat(s.cached_tokens.mean, digits=0),
        )
    console.print(table)


def write_results(runner: BenchmarkRunner, output_dir: str | Path) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = out / f"raw_{stamp}.json"
    report_path = out / f"report_{stamp}.md"

    payload: dict[str, Any] = runner.to_json()
    raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summaries = runner.summaries()
    report_path.write_text(build_markdown(summaries), encoding="utf-8")
    print_console(summaries)

    latest_raw = out / "raw_latest.json"
    latest_report = out / "report_latest.md"
    latest_raw.write_text(raw_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_report.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {"raw": raw_path, "report": report_path}
